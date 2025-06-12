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


# API Request/Response Models
class QuestionRequest(BaseModel):
    """Request model for asking questions."""

    question: str
    chat_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    model_provider: str = "openai"
    use_hybrid_search: bool = True


class QuestionResponse(BaseModel):
    """Response model for chat questions."""

    chat_id: int
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    context_used: List[str]
    metadata: Dict[str, Any]
    message_id: int


class SourceInfo(BaseModel):
    """Information about document sources."""

    chunk_id: str
    document_id: Optional[int] = None
    score: float
    preview: str


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    message: str
