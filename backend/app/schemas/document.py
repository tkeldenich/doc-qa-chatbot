from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class DocumentBase(BaseModel):
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_type: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None


class DocumentCreate(DocumentBase):
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    file_type: str
    content_hash: str


class DocumentUpdate(DocumentBase):
    processing_status: Optional[str] = None
    error_message: Optional[str] = None
    chunk_count: Optional[int] = None
    embedding_model: Optional[str] = None
    processed_at: Optional[datetime] = None


class DocumentInDBBase(DocumentBase):
    id: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    content_hash: Optional[str] = None
    processing_status: Optional[str] = None
    error_message: Optional[str] = None
    chunk_count: Optional[int] = None
    embedding_model: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True


class Document(DocumentInDBBase):
    pass


class DocumentInDB(DocumentInDBBase):
    pass
