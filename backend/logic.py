import random
# In-memory understanding tracker
concept_scores = {}  # concept → score (0 to 1)


# -------------------------
# UPDATE UNDERSTANDING
# -------------------------
def update_score(concept, score=0.5):
    concept_scores[concept] = score


# -------------------------
# GET WEAK CONCEPTS
# -------------------------
def get_weak_concepts():
    return [c for c, s in concept_scores.items() if s < 0.5]


# -------------------------
# GET RECOMMENDATIONS
# -------------------------
def get_recommendations():
    weak = get_weak_concepts()

    return {
        "weak_concepts": weak,
        "next_to_learn": list(concept_scores.keys())[:3],
        "revise": weak
    }


# -------------------------
# SIMPLE GRAPH (PLACEHOLDER)
# -------------------------
def get_graph_data():
    nodes = [{"id": i, "label": concept} for i, concept in enumerate(concept_scores.keys())]

    edges = []
    for i in range(len(nodes)):
        if i + 1 < len(nodes):
            edges.append({
                "source": nodes[i]["id"],
                "target": nodes[i + 1]["id"]
            })

        if i + 2 < len(nodes):
            edges.append({
                "source": nodes[i]["id"],
                "target": nodes[i + 2]["id"]
            })
    return {
        "nodes": nodes,
        "edges": edges
    }