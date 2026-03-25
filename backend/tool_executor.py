import json
from mcp_bridge import membrain_client


def execute_tool(tool_call):
    """
    Execute a tool call from the LLM.
    Updated to use the actual Membrain client.
    """
    try:
        name = tool_call["function"]["name"]
        
        # Parse arguments
        raw_args = tool_call["function"].get("arguments", {})
        
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                return {"error": "Invalid JSON arguments", "raw": raw_args}
        elif isinstance(raw_args, dict):
            args = raw_args
        else:
            return {"error": "Unsupported argument format"}
        
        # Common params
        user_id = args.get("user_id")
        if not user_id:
            return {"error": "Missing user_id"}
        
        # -------------------------
        # MEMBRAIN SEARCH
        # -------------------------
        if name == "membrain_search":
            query = args.get("query")
            k = args.get("k", 10)
            response_format = args.get("response_format", "interpreted")
            
            if not query:
                return {"error": "Missing 'query'"}
            
            result = membrain_client.semantic_search(
                query=query,
                user_id=user_id,
                k=k,
                response_format=response_format
            )
            
            return {
                "tool": "membrain_search",
                "query": query,
                "results": result.get("results", [])[:5],
                "summary": result.get("summary", ""),
                "key_facts": result.get("key_facts", [])
            }
        
        # -------------------------
        # MEMBRAIN ADD
        # -------------------------
        if name == "membrain_add":
            content = args.get("content")
            tags = args.get("tags", [])
            category = args.get("category", "general")
            
            if not content:
                return {"error": "Missing 'content'"}
            
            result = membrain_client.store_memory(
                content=content,
                user_id=user_id,
                tags=tags,
                category=category
            )
            
            return {
                "tool": "membrain_add",
                "success": result.get("success", False),
                "memory_id": result.get("memory_id"),
                "action": result.get("action"),
                "content": content
            }
        
        # -------------------------
        # MEMBRAIN GET
        # -------------------------
        if name == "membrain_get":
            memory_id = args.get("memory_id")
            
            if not memory_id:
                return {"error": "Missing 'memory_id'"}
            
            memory = membrain_client.get_memory(memory_id)
            
            if memory:
                return {
                    "tool": "membrain_get",
                    "memory": memory
                }
            return {"error": f"Memory {memory_id} not found"}
        
        return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        return {
            "error": "Tool execution failed",
            "details": str(e)
        }