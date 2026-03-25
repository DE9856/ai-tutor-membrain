import os
from dotenv import load_dotenv
from openai import OpenAI
from tool_executor import execute_tool

load_dotenv()

# OpenRouter client (OpenAI-compatible)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# -------------------------
# TOOL DEFINITIONS - Updated for Membrain API
# -------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "membrain_search",
            "description": "Semantic search over the user's memory graph. Use natural language questions. Returns memories and relationship edges.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language question or search query"},
                    "user_id": {"type": "string", "description": "User identifier"},
                    "k": {"type": "integer", "description": "Number of results to return (default 10)"},
                    "response_format": {"type": "string", "enum": ["raw", "interpreted", "both"], "description": "Format of response"}
                },
                "required": ["query", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "membrain_add",
            "description": "Store a new atomic fact or memory. Waits until ingest completes. Search first if unsure whether the fact already exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The fact or memory to store"},
                    "user_id": {"type": "string", "description": "User identifier"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags for categorization"},
                    "category": {"type": "string", "description": "Optional category"}
                },
                "required": ["content", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "membrain_get",
            "description": "Get a specific memory by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID to retrieve"},
                    "user_id": {"type": "string", "description": "User identifier"}
                },
                "required": ["memory_id", "user_id"]
            }
        }
    }
]


# -------------------------
# AGENT FUNCTION
# -------------------------
def run_agent(prompt: str, use_tools: bool = True):
    """Run agent with optional tool calling"""
    
    # For concept extraction, we often don't need tools
    if not use_tools:
        response = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI learning assistant helping extract concepts and relationships from notes. "
                        "Be precise, structured, and return only what is asked. "
                        "Do not add explanations unless requested."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3  # Lower temperature for extraction tasks
        )
        
        data = response.model_dump()
        return {
            "tool_executed": False,
            "response": data["choices"][0]["message"].get("content", "")
        }
    
    # For tool mode, call with tools
    response = client.chat.completions.create(
        model="meta-llama/llama-3-8b-instruct",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI learning assistant with memory. "
                    "Use membrain_search before answering questions. "
                    "Use membrain_add to store new facts. "
                    "Be concise and helpful."
                )
            },
            {"role": "user", "content": prompt}
        ],
        tools=tools,
        tool_choice="auto"
    )
    
    data = response.model_dump()
    message = data["choices"][0]["message"]
    tool_calls = message.get("tool_calls")
    
    if tool_calls:
        results = []
        for call in tool_calls:
            result = execute_tool(call)
            results.append(result)
        
        return {
            "tool_executed": True,
            "results": results
        }
    
    return {
        "tool_executed": False,
        "response": message.get("content", "")
    }