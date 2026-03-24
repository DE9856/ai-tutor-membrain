from pydantic import BaseModel

class NoteInput(BaseModel):
    text: str

class SearchInput(BaseModel):
    query: str