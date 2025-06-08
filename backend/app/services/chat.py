from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat, Message
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.base import CRUDBase


class CRUDChat(CRUDBase[Chat, ChatCreate, dict]):
    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Chat]:
        result = await db.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .where(Chat.is_active)
            .options(selectinload(Chat.messages))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_messages(
        self, db: AsyncSession, *, chat_id: int
    ) -> Optional[Chat]:
        result = await db.execute(
            select(Chat)
            .where(Chat.id == chat_id)
            .options(selectinload(Chat.messages))
        )
        return result.scalar_one_or_none()

    async def create_with_user(
        self, db: AsyncSession, *, obj_in: ChatCreate, user_id: int
    ) -> Chat:
        obj_in_data = obj_in.dict()
        obj_in_data["user_id"] = user_id
        db_obj = Chat(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDMessage(CRUDBase[Message, MessageCreate, dict]):
    async def get_by_chat(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_with_chat(
        self, db: AsyncSession, *, obj_in: MessageCreate, chat_id: int
    ) -> Message:
        obj_in_data = obj_in.dict()
        obj_in_data["chat_id"] = chat_id
        db_obj = Message(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


chat_service = CRUDChat(Chat)
message_service = CRUDMessage(Message)
