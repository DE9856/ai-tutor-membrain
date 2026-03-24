from fastapi import FastAPI
from models import NoteInput, SearchInput
from agent import run_agent
from logic import update_score, get_graph_data, get_recommendations
from note_processor import store_note_in_membrain

app = FastAPI()


@app.get("/")
def home():
    return {"message": "AI Tutor Backend Running 🚀"}


# -------------------------
# ADD NOTE
# -------------------------
@app.post("/add_note")
def add_note(data: NoteInput):
    result = store_note_in_membrain(data.text)

    # update scores per concept
    for concept in result["concepts"]:
        update_score(concept, 0.3)

    return result
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
    return get_graph_data()

# -------------------------
# RECOMMENDATIONS (TEMP)
# -------------------------
@app.get("/recommend")
def recommend():
    return get_recommendations()