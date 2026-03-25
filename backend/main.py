from fastapi import FastAPI, HTTPException
from typing import Optional
from models import (
    NoteInput, SearchInput, ConceptInput, AuthInput, 
    QuestionInput, ConceptDetailInput, UserSummaryInput
)
from agent import run_agent
from logic import (
    match_and_update, 
    get_graph_data, 
    get_recommendations,
    semantic_search_recommendations,
    get_learning_path,
    answer_question,
    get_concept_details,
    get_user_summary,
    get_weak_concepts,
    update_score
)
from mcp_bridge import membrain_client
from auth import signup_user, login_user

app = FastAPI(
    title="AI Tutor with Membrain",
    description="Fully dynamic learning assistant with semantic memory",
    version="2.0.0"
)


@app.get("/")
def home():
    return {
        "message": "AI Tutor Backend Running 🚀 - Fully Dynamic with Membrain",
        "version": "2.0.0",
        "endpoints": [
            "/learn_from_note", "/ask", "/search", "/recommendations/{user_id}",
            "/graph/{user_id}", "/learning_path/{user_id}", "/concept/{user_id}/{concept_name}",
            "/user_summary/{user_id}", "/weak_concepts/{user_id}", "/add_concept",
            "/signup", "/login"
        ]
    }

@app.get("/graph/neighborhood/{memory_id}")
def neighborhood(memory_id: str, hops: int = 2):
    """Get graph neighborhood around a specific memory"""
    return membrain_client.get_graph_neighborhood(memory_id, hops)

@app.get("/graph/hubs")
def hubs(limit: int = 10):
    """Get most connected concepts"""
    return membrain_client.get_graph_hubs(limit)

@app.get("/graph/neighborhood/by_name/{user_id}/{concept_name}")
def neighborhood_by_name(user_id: str, concept_name: str, hops: int = 2):
    """Get graph neighborhood by concept name"""
    # Find the concept ID first
    result = membrain_client.semantic_search(
        query=concept_name,
        user_id=user_id,
        k=1,
        response_format="raw",
        tag_filters=["type.concept"]
    )
    
    for item in result.get("results", []):
        if item.get("type") == "memory_node":
            memory_id = item.get("id")
            return membrain_client.get_graph_neighborhood(memory_id, hops)
    
    return {"error": f"Concept '{concept_name}' not found"}

@app.post("/learn_from_note")
def learn_from_note(data: NoteInput):
    """
    Learn from a note:
    - LLM extracts concepts and relationships
    - Stores everything in Membrain
    - Updates understanding scores
    """
    return match_and_update(data.text, data.user_id)


@app.post("/ask")
def ask_question(data: QuestionInput):
    """
    Ask a learning question:
    - Uses Membrain's semantic search
    - Returns interpreted answer with sources
    """
    return answer_question(data.user_id, data.question)


@app.post("/search")
def search(data: SearchInput):
    """Semantic search using Membrain"""
    result = membrain_client.semantic_search(
        query=data.query,
        user_id=data.user_id,
        k=data.k if hasattr(data, 'k') and data.k else 10,  # ✅ Use attribute access
        response_format="both"
    )
    return result

@app.get("/recommendations/{user_id}")
def recommend(user_id: str):
    """
    Get comprehensive learning recommendations:
    - Weak concepts to review
    - Next concepts to learn
    - Recent notes to revise
    """
    return get_recommendations(user_id)


@app.get("/graph/{user_id}")
def graph(user_id: str):
    """Get knowledge graph from Membrain using native graph export"""
    return membrain_client.get_native_graph_export(user_id)


@app.get("/learning_path/{user_id}")
def learning_path(user_id: str, target: Optional[str] = None):
    """
    Get personalized learning path:
    - Optimal concept order based on prerequisites
    - Estimated time per concept
    - Suggestions for resources
    """
    return get_learning_path(user_id, target)


@app.get("/concept/{user_id}/{concept_name}")
def concept_details(user_id: str, concept_name: str):
    """
    Get detailed information about a concept:
    - Mastery score
    - Relationships with other concepts
    - Related notes
    """
    return get_concept_details(user_id, concept_name)


@app.get("/user_summary/{user_id}")
def user_summary(user_id: str):
    """
    Get user learning summary:
    - Total concepts and notes
    - Average mastery
    - Weak and mastered concepts
    """
    return get_user_summary(user_id)


@app.get("/weak_concepts/{user_id}")
def weak_concepts(user_id: str):
    """
    Get concepts with low mastery scores
    """
    return {"weak_concepts": get_weak_concepts(user_id)}


@app.post("/add_concept")
def add_concept(data: ConceptInput):
    """
    Directly add a concept (for manual input)
    """
    result = membrain_client.store_concept(
        name=data.concept_name,
        user_id=data.user_id,
        metadata={
            "category": data.category or "core",
            "tags": data.tags or [],
            "understanding_score": 0.3
        }
    )
    return result


@app.post("/update_score")
def update_concept_score(user_id: str, concept: str, score: float):
    """
    Manually update a concept's understanding score
    """
    result = update_score(user_id, concept, 0)
    if result.get("success"):
        return {"success": True, "concept": concept, "new_score": score}
    return {"success": False, "error": "Could not update score"}


@app.post("/signup")
def signup(data: AuthInput):
    """Sign up a new user (Supabase auth)"""
    return signup_user(data.email, data.password)


@app.post("/login")
def login(data: AuthInput):
    """Login existing user (Supabase auth)"""
    return login_user(data.email, data.password)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "membrain_configured": bool(membrain_client.api_key),
        "api_url": membrain_client.base_url
    }


@app.get("/debug/relationships/{user_id}")
def debug_relationships(user_id: str):
    """Debug endpoint to see raw relationship content stored in Membrain"""
    rel_result = membrain_client.semantic_search(
        query="",
        user_id=user_id,
        k=200,
        response_format="raw",
        tag_filters=["type.relationship"]
    )

    relationships = []
    for rel in rel_result.get("results", []):
        if rel.get("type") != "memory_node":
            continue
        relationships.append({
            "id": rel.get("id"),
            "content": rel.get("content", ""),
            "tags": rel.get("tags", [])
        })

    # Also fetch nodes so you can cross-check
    concepts = membrain_client.get_concepts_for_user(user_id)
    node_names = [c.get("content", "").strip().lower() for c in concepts if c.get("content")]

    # For each relationship, show which node names were found inside it
    analysis = []
    for rel in relationships:
        content_lower = rel["content"].lower()
        matched_nodes = [n for n in node_names if n in content_lower]
        analysis.append({
            "content": rel["content"],
            "matched_nodes": matched_nodes,
            "will_produce_edge": len(matched_nodes) >= 2
        })

    return {
        "total_relationships": len(relationships),
        "total_nodes": len(node_names),
        "node_names": node_names,
        "analysis": analysis
    }