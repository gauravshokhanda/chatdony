from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com"
            }
        }

class MessageSend(BaseModel):
    sender_id: int
    receiver_id: int
    content: str

    class Config:
        schema_extra = {
            "example": {
                "sender_id": 1,
                "receiver_id": 2,
                "content": "Hey, how are you?"
            }
        }
