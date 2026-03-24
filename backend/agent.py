import os
from dotenv import load_dotenv
from openai import OpenAI
from tool_executor import execute_tool

# Load env
load_dotenv()

# OpenRouter client (OpenAI-compatible)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

# -------------------------
# TOOL DEFINITIONS
# -------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "membrain_add",
            "description": "Store a memory in Membrain",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "user_id": {"type": "string"}
                },
                "required": ["content", "user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "membrain_search",
            "description": "Search memories in Membrain",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "user_id": {"type": "string"}
                },
                "required": ["query", "user_id"]
            }
        }
    }
]

# -------------------------
# AGENT FUNCTION
# -------------------------
def run_agent(prompt: str, use_tools: bool = True):
    # -------------------------
    # API CALL
    # -------------------------
    response = client.chat.completions.create(
        model="meta-llama/llama-3-8b-instruct",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI learning assistant.\n"
                    "Be precise and structured."
                )
            },
            {"role": "user", "content": prompt}
        ],
        tools=tools if use_tools else None,
        tool_choice="auto" if use_tools else None
    )

    # -------------------------
    # EXTRACT RESPONSE
    # -------------------------
    data = response.model_dump()
    message = data["choices"][0]["message"]

    # -------------------------
    # TOOL MODE
    # -------------------------
    if use_tools:
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

    # -------------------------
    # TEXT MODE (NO TOOLS)
    # -------------------------
    return {
        "tool_executed": False,
        "response": message.get("content")
    }