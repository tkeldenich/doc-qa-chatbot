from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from .user import User


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Foreign Keys
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        String, nullable=False
    )  # user, assistant, system

    # Source attribution
    sources: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON
    )  # List of document chunks used
    chat_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON
    )  # Additional metadata (tokens, model, etc.)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Foreign Keys
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats.id"), nullable=False
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
