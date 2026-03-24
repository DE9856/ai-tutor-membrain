import json

def execute_tool(tool_call):
    name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])

    if name == "membrain_add":
        return {
            "action": "store",
            "content": args["content"],
            "note": "Handled by Membrain MCP"
        }

    if name == "membrain_search":
        return {
            "action": "search",
            "query": args["query"],
            "note": "Handled by Membrain MCP"
        }

    return {"error": "Unknown tool"}