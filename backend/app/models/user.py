# backend/app/models/user.py
from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field

class UserDocument(Document):
    email: Indexed(str, unique=True)
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
