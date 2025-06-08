from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.base import CRUDBase


class CRUDDocument(CRUDBase[Document, DocumentCreate, DocumentUpdate]):
    async def get_by_owner(
        self,
        db: AsyncSession,
        *,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        result = await db.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_hash(
        self, db: AsyncSession, *, content_hash: str
    ) -> Optional[Document]:
        result = await db.execute(
            select(Document).where(Document.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self, db: AsyncSession, *, status: str, skip: int = 0, limit: int = 100
    ) -> List[Document]:
        result = await db.execute(
            select(Document)
            .where(Document.processing_status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_owner(
        self, db: AsyncSession, *, obj_in: DocumentCreate, owner_id: int
    ) -> Document:
        obj_in_data = obj_in.dict()
        obj_in_data["owner_id"] = owner_id
        db_obj = Document(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


document_service = CRUDDocument(Document)
