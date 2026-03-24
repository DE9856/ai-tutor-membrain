import json

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

        memory_store.append(memory)

        return {
            "status": "stored",
            "memory": memory
        }

    # -------------------------
    # MEMBRAIN SEARCH
    # -------------------------
    elif function_name == "membrain_search":
        query = arguments["query"]

        results = [
            m for m in memory_store
            if query.lower() in m["content"].lower()
        ]

        return {
            "results": results
        }

    return {"error": "Unknown tool"}