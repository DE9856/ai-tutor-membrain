from fastapi import FastAPI
from models import NoteInput

app = FastAPI()

# Temporary storage (we’ll replace with Membrain later)
notes = []


@app.get("/")
def home():
    return {"message": "Backend is working 🚀"}


# -------------------------
# ADD NOTE
# -------------------------
@app.post("/add_note")
def add_note(data: NoteInput):
    notes.append(data.text)
    return {
        "status": "stored",
        "note": data.text
    }