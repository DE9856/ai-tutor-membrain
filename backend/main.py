from fastapi import FastAPI
from models import NoteInput, SearchInput
from agent import run_agent
from tool_executor import get_graph, get_recommendations

app = FastAPI()


@app.get("/")
def home():
    return {"message": "AI Tutor Backend Running 🚀"}


# -------------------------
# ADD NOTE
# -------------------------
@app.post("/add_note")
def add_note(data: NoteInput):
    prompt = f"""
You MUST store the following concept using the tool 'membrain_add'.

DO NOT explain anything.
DO NOT respond in text.

ONLY call the tool.

Content:
{data.text}
"""

    return run_agent(prompt)


# -------------------------
# SEARCH
# -------------------------
@app.post("/search")
def search(data: SearchInput):
    prompt = f"""
    You MUST call the tool 'membrain_search'.

    DO NOT explain anything.
    ONLY call the tool.

    Query:
    {data.query}
    """

    return run_agent(prompt)


@app.get("/graph")
def graph():
    return get_graph()

@app.get("/recommendations")
def recommendations():
    return get_recommendations()


