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
    Search for relevant concepts related to:
    {data.query}
    """

    return run_agent(prompt)