from fastapi import FastAPI
from models import NoteInput, SearchInput, ConceptInput, AuthInput
from agent import run_agent
from logic import update_score, get_graph_data, get_recommendations, match_and_update
from note_processor import store_note_in_membrain
from mcp_bridge import call_membrain
from auth import signup_user, login_user

app = FastAPI()


@app.get("/")
def home():
    return {"message": "AI Tutor Backend Running 🚀"}


# -------------------------
# ADD NOTE
# -------------------------
@app.post("/add_note")
def add_note(data: NoteInput):
    user_id = data.user_id  # 🔥 NEW

    # pass user_id to processor
    result = store_note_in_membrain(data.text, user_id)  # 🔥 UPDATED


    # match note content against existing concepts
    match_and_update(data.text,user_id)

    return result


#--------------------------
# LEARN (FROM NOTES)
#--------------------------
@app.post("/learn")
def learn(data: NoteInput):
    user_id = data.user_id

    # 🔥 update scores
    match_and_update(data.text, user_id)

    # 🔥 ALSO store in DB
    store_note_in_membrain(data.text, user_id)

    return {
        "status": "learning_updated",
        "message": "Concept scores updated + stored"
    }

# -------------------------
# ADD CONCEPT
# -------------------------
@app.post("/add_concept")
def add_concept(data: ConceptInput):
    user_id = data.user_id
    concept_name = data.concept_name
    category = data.category or "core"
    tags = data.tags or []
    
    # Initialize concept in scores
    update_score(user_id, concept_name)
    
    # Store concept to membrain
    concept_metadata = f"[CONCEPT] {concept_name} | Category: {category} | Tags: {', '.join(tags) if tags else 'none'}"
    result = call_membrain("add", concept_metadata, user_id)
    
    return {
        "success": True,
        "memory_id": concept_name,
        "message": f"✨ '{concept_name}' added to knowledge graph!",
        "concept": concept_name,
        "category": category,
        "tags": tags
    }

# -------------------------
# SEARCH
# -------------------------
@app.post("/search")
def search(data: SearchInput):
    # 🔥 OPTIONAL: if you later add user_id to SearchInput
    # user_id = getattr(data, "user_id", "default_user")

    prompt = f"""
You MUST call the tool 'membrain_search'.

DO NOT explain anything.
ONLY call the tool.

Query:
{data.query}
User:
{data.user_id}
"""
    return run_agent(prompt)


# -------------------------
# GRAPH (TEMP — based on in-memory)
# -------------------------
@app.get("/graph/{user_id}")
def graph(user_id: str):
    return get_graph_data(user_id)


# -------------------------
# RECOMMENDATIONS (TEMP)
# -------------------------
@app.get("/recommend/{user_id}")
def recommend(user_id: str):
    return get_recommendations(user_id)

# -------------------------
# SIGN UP
# -------------------------
@app.post("/signup")
def signup(data: AuthInput):
    return signup_user(data.email, data.password)


# -------------------------
# LOGIN
# -------------------------
@app.post("/login")
def login(data: AuthInput):
    return login_user(data.email, data.password)