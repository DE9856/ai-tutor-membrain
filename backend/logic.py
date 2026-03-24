import re
import json
from agent import run_agent
import mcp_bridge

# 🔥 user_id → {concept → score}
concept_scores = {}


# -------------------------
# NORMALIZE CONCEPT
# -------------------------
def normalize(concept):
    return concept.strip().lower().title()


# -------------------------
# UPDATE UNDERSTANDING
# -------------------------
def update_score(user_id, concept):
    concept = normalize(concept)

    if user_id not in concept_scores:
        concept_scores[user_id] = {}

    if concept in concept_scores[user_id]:
        concept_scores[user_id][concept] = min(
            1.0,
            concept_scores[user_id][concept] + 0.1
        )
    else:
        concept_scores[user_id][concept] = 0.3


# -------------------------
# MATCH NOTE → EXISTING TOPICS
# -------------------------
def match_and_update(note_text, user_id):
    note = note_text.lower()
    matched = False

    user_data = concept_scores.get(user_id, {})

    for concept in list(user_data.keys()):
        words = concept.lower().split()

        if any(word in note for word in words):
            update_score(user_id, concept)
            matched = True

    # 🔥 IF NOTHING MATCHED → EXTRACT NEW TOPIC(S)
    if not matched:
        prompt = f"""
Extract 1 or 2 main concepts from this text.

RULES:
- Max 2 concepts
- Each concept max 3 words
- NO numbering
- NO bullets
- NO explanation
- Return each concept on a new line

Text:
{note_text}
"""
        response = run_agent(prompt, use_tools=False)

        try:
            raw_output = response["response"]
        except:
            return

        lines = raw_output.split("\n")

        for line in lines:
            line = line.strip()

            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            line = line.lstrip("-• ").strip()

            if (
                not line
                or len(line.split()) > 3
                or any(x in line.lower() for x in ["concept", "here", "topic"])
            ):
                continue

            update_score(user_id, line)


# -------------------------
# GET WEAK CONCEPTS
# -------------------------
def get_weak_concepts(user_id):
    user_data = concept_scores.get(user_id, {})
    return [c for c, s in user_data.items() if s < 0.5]


# -------------------------
# GET RECOMMENDATIONS
# -------------------------
def get_recommendations(user_id):
    user_data = concept_scores.get(user_id, {})

    weak = get_weak_concepts(user_id)
    sorted_concepts = sorted(user_data.items(), key=lambda x: x[1])

    next_to_learn = [c for c, _ in sorted_concepts[:3]]

    return {
        "weak_concepts": weak,
        "next_to_learn": next_to_learn,
        "revise": weak
    }


# -------------------------
# SAFE JSON PARSE
# -------------------------
def safe_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                return []
        return []


# -------------------------
# FUZZY MATCH (CRITICAL)
# -------------------------
def find_best_match(name, concept_list):
    if not name:
        return None

    name = name.lower()

    for concept in concept_list:
        c = concept.lower()

        if name == c:
            return concept

        if name in c or c in name:
            return concept

    return None


# -------------------------
# LLM RELATION EXTRACTION
# -------------------------
def extract_relationships_with_llm(note, concept_list):
    prompt = f"""
Given these concepts:

{chr(10).join(concept_list)}

And this note:
"{note}"

Extract ONLY EXPLICIT relationships.

STRICT RULES:
- ONLY if clearly stated
- DO NOT guess
- DO NOT infer
- ONLY use given concepts

Return EXACT JSON ONLY:
[
  {{"source": "EXACT_CONCEPT_NAME", "target": "EXACT_CONCEPT_NAME", "relation": "relation_type"}}
]

If no relation → return []
"""

    response = run_agent(prompt, use_tools=False)

    try:
        return safe_parse(response["response"])
    except:
        return []


# -------------------------
# VALIDATION
# -------------------------
def is_valid_relation(note, source, target):
    note = note.lower()
    s = source.lower()
    t = target.lower()

    if s not in note or t not in note:
        return False

    relation_keywords = [
        "is a part of",
        "part of",
        "belongs to",
        "type of",
        "example of",
        "uses",
        "depends on",
        "includes",
        "consists of",
        "subset of"
    ]

    return any(keyword in note for keyword in relation_keywords)


# -------------------------
# GRAPH DATA (FINAL 🔥)
# -------------------------
def get_graph_data(user_id):

    user_data = concept_scores.get(user_id, {})
    concept_list = list(user_data.keys())

    nodes = [
        {"id": i, "label": concept}
        for i, concept in enumerate(concept_list)
    ]

    edges = []

    # ✅ fetch notes
    try:
        response = mcp_bridge.supabase.table("memories") \
            .select("content") \
            .eq("user_id", user_id) \
            .execute()

        notes = [item["content"] for item in response.data]

    except Exception as e:
        print("DB error:", e)
        notes = []

    # ✅ build relations
    for note in notes:
        relations = extract_relationships_with_llm(note, concept_list)

        for rel in relations:
            raw_src = rel.get("source")
            raw_tgt = rel.get("target")

            src = find_best_match(raw_src, concept_list)
            tgt = find_best_match(raw_tgt, concept_list)

            if (
                src
                and tgt
                and src != tgt
                and is_valid_relation(note, src, tgt)
            ):
                edges.append({
                    "source": concept_list.index(src),
                    "target": concept_list.index(tgt),
                    "label": rel.get("relation", "related")
                })

    # ✅ remove duplicates
    edges = list({
        (e["source"], e["target"]): e for e in edges
    }.values())

    return {
        "nodes": nodes,
        "edges": edges
    }