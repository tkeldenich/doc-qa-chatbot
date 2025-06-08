from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    JSON,
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


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, unique=True, index=True)

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String, default="pending"
    )  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    doc_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[Optional[str]] = mapped_column(String)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Foreign Keys
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")

    # Indexes and constraints
    __table_args__ = {"extend_existing": True}
