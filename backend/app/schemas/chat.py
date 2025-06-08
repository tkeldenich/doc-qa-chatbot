from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MessageBase(BaseModel):
    content: str
    role: str
    sources: Optional[List[Dict[str, Any]]] = None
    chat_metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: int
    created_at: datetime
    chat_id: int

    class Config:
        from_attributes = True


class ChatBase(BaseModel):
    title: str
    is_active: Optional[bool] = True


class ChatCreate(ChatBase):
    pass


class Chat(ChatBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int
    messages: List[Message] = []

    class Config:
        from_attributes = True
