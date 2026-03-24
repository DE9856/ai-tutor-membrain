import json
from mcp_bridge import call_membrain

# Temporary in-memory store (acts like Membrain for now)
memory_store = []


def execute_tool(tool_call):
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])

    # -------------------------
    # MEMBRAIN ADD
    # -------------------------
    if function_name == "membrain_add":
        content = arguments["content"]

        memory = {
            "id": len(memory_store),
            "content": content
        }

        return call_membrain("add", content)

    # -------------------------
    # MEMBRAIN SEARCH
    # -------------------------
    elif function_name == "membrain_search":
        query = arguments["query"]

        return call_membrain("search", query)

    return {"error": "Unknown tool"}

def get_graph():
    nodes = [{"id": m["id"], "label": m["content"]} for m in memory_store]

    edges = []
    for i in range(len(memory_store) - 1):
        edges.append({
            "source": memory_store[i]["id"],
            "target": memory_store[i + 1]["id"]
        })

    return {
        "nodes": nodes,
        "edges": edges
    }


understanding = {"Machine Learning is a subset of AI": 0.3, "Neural Networks are a part of deep learning": 0.8}
def update_understanding(concept, score):
    understanding[concept] = score

def get_recommendations():
    weak_concepts = [k for k, v in understanding.items() if v < 0.5]

    next_to_learn = weak_concepts[:2]

    revise = weak_concepts

    return {
        "weak_concepts": weak_concepts,
        "next_to_learn": next_to_learn,
        "revise": revise
    }