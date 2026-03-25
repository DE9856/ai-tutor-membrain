"""
Fully dynamic logic - LLM for everything, Membrain for storage
Complete with all original functionality: chunking, extraction, relationships, recommendations, learning path
No hardcoded topics, no keyword matching
"""

import re
import json
import time
from typing import List, Dict, Optional, Any, Tuple
from agent import run_agent
from mcp_bridge import membrain_client


# -------------------------
# HELPER FUNCTIONS
# -------------------------

def safe_json_parse(text: str) -> Any:
    """Safely parse JSON from LLM response with multiple fallbacks"""
    if not text:
        return {}
    
    # Remove markdown code blocks
    text = re.sub(r'```json\n?', '', text)
    text = re.sub(r'\n?```', '', text)
    text = text.strip()
    
    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass
    
    # Try to extract JSON from text
    json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    return {}


def clean_concept_name(name: str) -> str:
    """Clean and normalize concept names"""
    if not name:
        return ""
    name = name.strip()
    name = re.sub(r'^\d+[\.\)]\s*', '', name)
    name = re.sub(r'^[\-\*•]\s*', '', name)
    name = name.strip()
    # Capitalize first letter of each word
    return ' '.join(word.capitalize() for word in name.split())


def split_into_chunks(text: str, max_len: int = 200) -> List[str]:
    """Split long notes into manageable chunks for processing"""
    words = text.split()
    chunks = []
    current = []
    current_len = 0
    
    for word in words:
        word_len = len(word) + 1
        if current_len + word_len > max_len and current:
            chunks.append(' '.join(current))
            current = [word]
            current_len = word_len
        else:
            current.append(word)
            current_len += word_len
    
    if current:
        chunks.append(' '.join(current))
    
    return chunks


def extract_concepts_from_chunk(chunk: str, existing_concepts: List[str] = None) -> List[str]:
    """Extract concepts from a single text chunk using LLM"""
    context = ""
    if existing_concepts:
        context = f"\nExisting concepts (use these exact names if matching): {', '.join(existing_concepts[:10])}\n"
    
    prompt = f"""
Extract ONLY the main learning concepts from this text.

STRICT RULES:
- MAX 3 concepts per chunk
- Each concept MUST be 1-3 words
- Use standard technical terms
- NO explanations, NO sentences, NO numbering
- Return each concept on a new line
{context}

Text:
{chunk}
"""
    
    response = run_agent(prompt, use_tools=False)
    
    try:
        content = response["response"] if isinstance(response, dict) else str(response)
        lines = content.split('\n')
        concepts = []
        
        for line in lines:
            cleaned = clean_concept_name(line)
            if cleaned and len(cleaned.split()) <= 3 and len(cleaned) > 2:
                if not any(x in cleaned.lower() for x in ['concept', 'here', 'topic', 'extract']):
                    concepts.append(cleaned)
        
        return concepts[:3]
    except:
        return []


def extract_relationships_between_concepts(note: str, concepts: List[str]) -> List[Dict]:
    """Extract relationships between concepts mentioned in the note using LLM"""
    if len(concepts) < 2:
        return []
    
    prompt = f"""
Given these concepts: {', '.join(concepts)}

And this note: "{note}"

Extract relationships between these concepts ONLY if explicitly stated or strongly implied.

Return EXACT JSON ONLY (no other text):
[
  {{"source": "EXACT_CONCEPT_NAME", "target": "EXACT_CONCEPT_NAME", "type": "relationship_type"}}
]

Relationship types: "prerequisite", "part_of", "example_of", "related_to", "contrasts_with", "depends_on", "subset_of"

If no relationships: return []
"""
    
    response = run_agent(prompt, use_tools=False)
    
    try:
        content = response["response"] if isinstance(response, dict) else str(response)
        result = safe_json_parse(content)
        if isinstance(result, list):
            return result
        return []
    except:
        return []


def get_existing_concepts_context(user_id: str, limit: int = 20) -> Tuple[List[str], str]:
    """Get existing concepts for context in extraction"""
    concepts = membrain_client.get_concepts_for_user(user_id, limit=limit)
    concept_names = [c.get("content") for c in concepts]
    
    # Also get scores for context
    concept_context = []
    for name in concept_names[:15]:
        score = membrain_client.get_concept_score(name, user_id)
        mastery = "high" if score > 0.7 else "medium" if score > 0.3 else "low"
        concept_context.append(f"- {name} (mastery: {mastery})")
    
    context_str = "\n".join(concept_context) if concept_context else "No existing concepts yet."
    
    return concept_names, context_str


# -------------------------
# MAIN PROCESSING FUNCTIONS
# -------------------------

def extract_concepts_and_relationships(note_text: str, user_id: str, 
                                       existing_concepts: List[str] = None) -> Dict:
    """
    Extract concepts and relationships from a note using LLM
    Fully dynamic - no hardcoded topics
    """
    existing, context_str = get_existing_concepts_context(user_id)
    if existing_concepts is None:
        existing_concepts = existing
    
    prompt = f"""
Analyze this learning note and extract:
1. The main concepts (1-3 concepts, 1-3 words each)
2. How these concepts relate to each other

Existing concepts in your knowledge base:
{context_str}

Note: "{note_text}"

Return EXACT JSON format (no other text):
{{
  "concepts": ["Concept 1", "Concept 2", "Concept 3"],
  "relationships": [
    {{"source": "Concept 1", "target": "Concept 2", "type": "prerequisite"}}
  ]
}}

Rules:
- If a concept matches an existing one, use the EXACT same name
- Relationship types: prerequisite, part_of, example_of, related_to, contrasts_with, depends_on, subset_of
- Max 3 concepts, max 3 relationships
- NEVER extract generic words as concepts: subset, subfield, type, part, kind, form, field, domain, model, layer
- Only extract proper technical concept names like "Machine Learning", "Neural Networks", "Transformers"
"""
    
    response = run_agent(prompt, use_tools=False)
    
    try:
        content = response["response"] if isinstance(response, dict) else str(response)
        result = safe_json_parse(content)
        
        # Ensure we have the expected structure
        if isinstance(result, dict):
            concepts = result.get("concepts", [])
            relationships = result.get("relationships", [])
            # Clean concept names
            concepts = [clean_concept_name(c) for c in concepts if c]
            return {
                "concepts": concepts[:3],
                "relationships": relationships[:3]
            }
        
        return {"concepts": [], "relationships": []}
        
    except Exception as e:
        print(f"Extraction error: {e}")
        return {"concepts": [], "relationships": []}


def match_and_update(note_text: str, user_id: str) -> Dict:
    """
    Fully dynamic processing:
    1. Split long notes into chunks
    2. Extract concepts and relationships using LLM
    3. Store concepts in Membrain with scores
    4. Store relationships as linked memories
    5. Store the original note
    """
    
    # Split long notes into chunks
    chunks = split_into_chunks(note_text)
    
    all_concepts = []
    all_relationships = []
    stored_concepts = []
    stored_relationships = []
    
    # Get existing concepts once for context
    existing_concepts, _ = get_existing_concepts_context(user_id)
    
    for chunk in chunks:
        # Extract concepts and relationships for this chunk
        extracted = extract_concepts_and_relationships(chunk, user_id, existing_concepts)
        concepts = extracted.get("concepts", [])
        relationships = extracted.get("relationships", [])
        
        # Add to master lists
        for concept in concepts:
            if concept not in all_concepts:
                all_concepts.append(concept)
        
        for rel in relationships:
            all_relationships.append(rel)
        
        # Store concepts in Membrain and update scores
        for concept in concepts:
            if not concept or len(concept) < 2:
                continue
            
            # Check if concept already exists
            existing = membrain_client.get_concept_by_name(concept, user_id)
            
            if existing:
                current_score = membrain_client.get_concept_score(concept, user_id)
                new_score = min(1.0, current_score + 0.1)
                membrain_client.update_concept_score(concept, user_id, new_score)
                stored_concepts.append({
                    "name": concept, 
                    "action": "updated", 
                    "score": new_score
                })
            else:
                membrain_client.store_concept(concept, user_id, {
                    "category": "core",
                    "understanding_score": 0.3,
                    "first_seen": time.time()
                })
                stored_concepts.append({
                    "name": concept, 
                    "action": "created", 
                    "score": 0.3
                })
    
    # Store relationships
    for rel in all_relationships:
        source = rel.get("source")
        target = rel.get("target")
        rel_type = rel.get("type", "related")
        
        if source and target and source != target:
            # Clean concept names
            source = clean_concept_name(source)
            target = clean_concept_name(target)
            
            # Ensure both concepts exist
            if source not in all_concepts:
                all_concepts.append(source)
                membrain_client.store_concept(source, user_id, {"understanding_score": 0.3})
            if target not in all_concepts:
                all_concepts.append(target)
                membrain_client.store_concept(target, user_id, {"understanding_score": 0.3})
            
            # Store relationship
            result = membrain_client.store_relationship(source, target, rel_type, user_id)
            
            stored_relationships.append({
                "source": source,
                "target": target,
                "type": rel_type,
                "stored": result.get("success", False)
            })
    
    # Store the original note with references to all concepts
    note_result = membrain_client.store_note(note_text, user_id, all_concepts)
    
    return {
        "concepts_extracted": all_concepts,
        "relationships_extracted": all_relationships,
        "concepts_stored": stored_concepts,
        "relationships_stored": stored_relationships,
        "note_stored": note_result.get("success", False),
        "chunks_processed": len(chunks),
        "user_id": user_id
    }


def update_score(user_id: str, concept: str, increment: float = 0.1) -> Dict:
    """Update concept understanding score in Membrain"""
    current = membrain_client.get_concept_score(concept, user_id)
    new_score = min(1.0, current + increment)
    return membrain_client.update_concept_score(concept, user_id, new_score)


def get_weak_concepts(user_id: str) -> List[str]:
    """Get concepts with understanding score < 0.5"""
    concepts = membrain_client.get_concepts_for_user(user_id)
    weak = []
    
    for concept in concepts:
        name = concept.get("content")
        score = membrain_client.get_concept_score(name, user_id)
        if score < 0.5:
            weak.append(name)
    
    return weak


def get_recommendations(user_id: str) -> Dict:
    """Get comprehensive learning recommendations"""
    concepts = membrain_client.get_concepts_for_user(user_id)
    
    weak_concepts = []
    mastered_concepts = []
    concepts_with_scores = []
    
    for concept in concepts:
        name = concept.get("content")
        score = membrain_client.get_concept_score(name, user_id)
        concepts_with_scores.append({"name": name, "score": score})
        
        if score < 0.5:
            weak_concepts.append({
                "name": name,
                "score": score,
                "reason": "Low mastery score"
            })
        elif score > 0.8:
            mastered_concepts.append({
                "name": name,
                "score": score,
                "reason": "Well understood"
            })
    
    # Sort by score (lowest first for next to learn)
    concepts_with_scores.sort(key=lambda x: x["score"])
    next_to_learn = []
    
    for c in concepts_with_scores[:5]:
        if c["score"] < 0.7:
            # Find prerequisites if any
            prereqs = []
            relationships = membrain_client.get_relationships_for_concept(c["name"], user_id)
            for rel in relationships:
                content = rel.get("content", "")
                if "prerequisite" in content or "depends_on" in content:
                    prereqs.append(content)
            
            next_to_learn.append({
                "name": c["name"],
                "score": c["score"],
                "prerequisites": prereqs[:2],
                "estimated_time": "30-60 mins"
            })
    
    # Get recent notes for review suggestions
    recent_notes = membrain_client.get_notes_for_user(user_id, limit=5)
    revise_now = []
    
    for note in recent_notes:
        revise_now.append({
            "name": note.get("content", "")[:50] + "...",
            "importance": "Medium",
            "reason": "Recent note - review to reinforce"
        })
    
    return {
        "weak_concepts": weak_concepts,
        "mastered_concepts": mastered_concepts,
        "next_to_learn": next_to_learn,
        "revise_now": revise_now[:3],
        "total_concepts": len(concepts),
        "total_notes": len(recent_notes)
    }


def get_learning_path(user_id: str, target_concept: str = None) -> Dict:
    """
    Generate a dynamic learning path based on concept mastery and relationships
    Uses LLM to suggest optimal learning order
    """
    concepts = membrain_client.get_concepts_for_user(user_id)
    
    if not concepts:
        return {
            "path": [],
            "message": "Add some concepts to get a learning path",
            "suggestions": []
        }
    
    # Get all concepts with scores and relationships
    concept_data = []
    for concept in concepts:
        name = concept.get("content")
        score = membrain_client.get_concept_score(name, user_id)
        
        # Get relationships
        rels = membrain_client.get_relationships_for_concept(name, user_id)
        prerequisites = []
        related = []
        
        for rel in rels:
            content = rel.get("content", "")
            if "prerequisite" in content or "depends_on" in content:
                prerequisites.append(content)
            else:
                related.append(content)
        
        concept_data.append({
            "name": name,
            "mastery": score,
            "prerequisites": prerequisites[:3],
            "related": related[:3]
        })
    
    # Sort by mastery (lowest first)
    concept_data.sort(key=lambda x: x["mastery"])
    weak_concepts = [c["name"] for c in concept_data if c["mastery"] < 0.5]
    
    # Use LLM to generate learning path
    context = f"""
User's concepts and mastery levels:
{json.dumps(concept_data, indent=2)[:2000]}

Weak concepts (need attention): {', '.join(weak_concepts[:5])}

{f"Target concept to learn: {target_concept}" if target_concept else ""}
"""
    
    prompt = f"""
{context}

Based on this learning graph, create a personalized learning path.

Return JSON ONLY:
{{
  "path": [
    {{"step": 1, "concept": "Concept name", "reason": "Why learn this first", "estimated_time": "X hours"}},
    {{"step": 2, "concept": "Concept name", "reason": "Why next", "estimated_time": "X hours"}}
  ],
  "prerequisites_to_review": ["concept1", "concept2"],
  "suggestions": ["Specific resource or exercise suggestion"],
  "total_estimated_time": "X hours"
}}

Max 5 steps in path.
"""
    
    response = run_agent(prompt, use_tools=False)
    
    try:
        content = response["response"] if isinstance(response, dict) else str(response)
        result = safe_json_parse(content)
        
        if isinstance(result, dict):
            return result
        
        # Fallback to simple path
        return {
            "path": [
                {"step": i+1, "concept": c["name"], 
                 "reason": f"Current mastery: {c['mastery']:.0%}", 
                 "estimated_time": "30 mins"}
                for i, c in enumerate(concept_data[:5])
            ],
            "prerequisites_to_review": [],
            "suggestions": ["Review the weakest concepts first"],
            "total_estimated_time": "2-3 hours"
        }
        
    except Exception as e:
        print(f"Learning path error: {e}")
        return {
            "path": [],
            "message": "Could not generate learning path",
            "suggestions": [f"Review: {c['name']}" for c in concept_data[:3]]
        }


def semantic_search_recommendations(user_id: str, query: str, k: int = 10) -> Dict:
    """
    Use Membrain's semantic search to find relevant content
    Returns interpreted summary + raw results
    """
    result = membrain_client.semantic_search(
        query=query,
        user_id=user_id,
        k=k,
        response_format="both"
    )
    
    return {
        "query": query,
        "success": result.get("success", False),
        "summary": result.get("summary", ""),
        "key_facts": result.get("key_facts", []),
        "relevant_memories": result.get("results", [])[:5],
        "total_found": len(result.get("results", []))
    }


def answer_question(user_id: str, question: str) -> Dict:
    """
    Answer a learning question using Membrain's semantic search
    Falls back to LLM synthesis if needed
    """
    # First, search Membrain semantically
    search_result = membrain_client.semantic_search(
        query=question,
        user_id=user_id,
        k=10,
        response_format="both"
    )
    
    # If Membrain's interpreted summary is good, use it
    if search_result.get("summary") and not search_result.get("interpreted_error"):
        return {
            "answer": search_result.get("summary"),
            "sources": search_result.get("results", [])[:3],
            "key_facts": search_result.get("key_facts", []),
            "method": "membrain_interpreted",
            "confidence": "high"
        }
    
    # Otherwise, have LLM synthesize answer from raw results
    raw_results = search_result.get("results", [])
    
    if not raw_results:
        return {
            "answer": "I don't have any information about that yet. Try adding some notes or concepts first!",
            "sources": [],
            "key_facts": [],
            "method": "no_results",
            "confidence": "low"
        }
    
    # Format results for LLM
    context_parts = []
    for result in raw_results[:5]:
        if result.get("type") == "memory_node":
            context_parts.append(f"- {result.get('content')}")
        elif result.get("type") == "relationship_edge":
            context_parts.append(f"- {result.get('description')}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""
Based on this knowledge from the user's learning graph:

{context}

Answer this question: "{question}"

Be concise, accurate, and cite specific concepts when possible.
If the information doesn't fully answer the question, say so.
"""
    
    response = run_agent(prompt, use_tools=False)
    answer = response["response"] if isinstance(response, dict) else str(response)
    
    return {
        "answer": answer,
        "sources": raw_results[:3],
        "key_facts": search_result.get("key_facts", []),
        "method": "llm_synthesized",
        "confidence": "medium"
    }


def get_graph_data(user_id: str) -> Dict:
    """Get graph data from Membrain for visualization"""
    return membrain_client.get_graph_export(user_id)


def get_concept_details(user_id: str, concept_name: str) -> Dict:
    """Get detailed information about a specific concept"""
    concept = membrain_client.get_concept_by_name(concept_name, user_id)
    
    if not concept:
        return {"error": f"Concept '{concept_name}' not found"}
    
    score = membrain_client.get_concept_score(concept_name, user_id)
    relationships = membrain_client.get_relationships_for_concept(concept_name, user_id)
    notes = membrain_client.semantic_search(
        query=concept_name,
        user_id=user_id,
        k=10,
        response_format="raw",
        tag_filters=["type.note", f"references.{concept_name.replace(' ', '_')}"]
    )
    
    return {
        "name": concept_name,
        "score": score,
        "tags": concept.get("tags", []),
        "relationships": [
            {"content": r.get("content"), "id": r.get("id")}
            for r in relationships
        ],
        "related_notes": [
            {"content": n.get("content"), "id": n.get("id")}
            for n in notes.get("results", []) if n.get("type") == "memory_node"
        ][:5]
    }


def get_user_summary(user_id: str) -> Dict:
    """Get a summary of the user's learning progress"""
    concepts = membrain_client.get_concepts_for_user(user_id)
    notes = membrain_client.get_notes_for_user(user_id)
    
    total_concepts = len(concepts)
    total_notes = len(notes)
    
    if total_concepts == 0:
        return {
            "total_concepts": 0,
            "total_notes": total_notes,
            "average_mastery": 0,
            "weak_concepts": [],
            "mastered_concepts": [],
            "recommendations": ["Add your first concept to start learning!"]
        }
    
    scores = []
    weak = []
    mastered = []
    
    for concept in concepts:
        name = concept.get("content")
        score = membrain_client.get_concept_score(name, user_id)
        scores.append(score)
        
        if score < 0.5:
            weak.append(name)
        elif score > 0.8:
            mastered.append(name)
    
    avg_score = sum(scores) / len(scores)
    
    return {
        "total_concepts": total_concepts,
        "total_notes": total_notes,
        "average_mastery": round(avg_score, 2),
        "weak_concepts": weak[:5],
        "mastered_concepts": mastered[:5],
        "recommendations": [
            f"Review: {weak[0]}" if weak else "Great job! Keep adding new concepts",
            f"Explore relationships in: {concepts[0].get('content')}" if concepts else "Add a note to get started"
        ]
    }