def call_membrain(action: str, content: str):
    """
    This function represents the bridge to Membrain MCP.
    Right now it simulates sending requests to Membrain.

    In real setup, this would connect to MCP runtime (Cursor).
    """

    if action == "add":
        return {
            "membrain": "add",
            "status": "sent_to_membrain",
            "content": content
        }

    if action == "search":
        return {
            "membrain": "search",
            "status": "query_sent",
            "query": content
        }

    return {"error": "invalid action"}