import os
from dotenv import load_dotenv
from openai import OpenAI

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
                    "content": {"type": "string"}
                },
                "required": ["content"]
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
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]

# -------------------------
# AGENT FUNCTION
# -------------------------
def run_agent(prompt: str):
    response = client.chat.completions.create(
        model="meta-llama/llama-3-8b-instruct",
        messages=[
            {"role": "system", "content": "You are an AI tutor that MUST use tools."},
            {"role": "user", "content": prompt}
        ],
        tools=tools,
        tool_choice="auto"  # try "required" if supported
    )

    return response.model_dump()