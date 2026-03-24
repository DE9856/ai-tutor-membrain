import json
from mcp_bridge import call_membrain


def execute_tool(tool_call):
    try:
        name = tool_call["function"]["name"]

        # -------------------------
        # SAFE ARG PARSING
        # -------------------------
        raw_args = tool_call["function"].get("arguments", {})

        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                return {
                    "error": "Invalid JSON arguments",
                    "raw": raw_args
                }

        elif isinstance(raw_args, dict):
            args = raw_args

        else:
            return {
                "error": "Unsupported argument format",
                "raw": str(raw_args)
            }

        # -------------------------
        # TOOL HANDLING
        # -------------------------
        if name == "membrain_add":
            content = args.get("content")
            if not content:
                return {"error": "Missing 'content'"}
            return call_membrain("add", content)

        if name == "membrain_search":
            query = args.get("query")
            if not query:
                return {"error": "Missing 'query'"}
            return call_membrain("search", query)

        return {"error": f"Unknown tool: {name}"}

    except Exception as e:
        return {
            "error": "Tool execution failed",
            "details": str(e)
        }