from fastapi import FastAPI
from models import NoteInput, SearchInput
from agent import run_agent

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


# -------------------------
# GRAPH (TEMP — based on search)
# -------------------------
@app.get("/graph")
def graph():
    # simple placeholder (since real graph not exposed via API)
    return {
        "message": "Graph will be derived from Membrain in frontend",
        "status": "using Membrain backend"
    }


# -------------------------
# RECOMMENDATIONS (TEMP)
# -------------------------
@app.get("/recommendations")
def recommendations():
    return {
        "weak_concepts": [],
        "next_to_learn": ["Try searching your stored concepts"],
        "revise": []
    }