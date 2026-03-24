from pydantic import BaseModel

class NoteInput(BaseModel):
    text: str