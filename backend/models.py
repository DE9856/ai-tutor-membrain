from pydantic import BaseModel
from typing import Optional, List

class NoteInput(BaseModel):
    text: str
    user_id: str

class SearchInput(BaseModel):
    query: str
    user_id: str

class ConceptInput(BaseModel):
    concept_name: str
    user_id: str
    category: Optional[str] = "core"
    tags: Optional[List[str]] = None

class AuthInput(BaseModel):
    email: str
    password: str

