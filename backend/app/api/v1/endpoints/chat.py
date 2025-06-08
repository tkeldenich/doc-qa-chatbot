from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import Chat as ChatSchema
from app.schemas.chat import ChatCreate
from app.schemas.chat import Message as MessageSchema
from app.schemas.chat import MessageCreate
from app.services.chat import chat_service, message_service

router = APIRouter()


@router.get("/", response_model=List[ChatSchema])
async def read_chats(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve chats for current user."""
    chats = await chat_service.get_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return chats


@router.post("/", response_model=ChatSchema)
async def create_chat(
    *,
    db: AsyncSession = Depends(get_db),
    chat_in: ChatCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create new chat."""
    chat = await chat_service.create_with_user(
        db=db, obj_in=chat_in, user_id=current_user.id
    )
    return chat


@router.get("/{chat_id}", response_model=ChatSchema)
async def read_chat(
    *,
    db: AsyncSession = Depends(get_db),
    chat_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get chat by ID with messages."""
    chat = await chat_service.get_with_messages(db=db, chat_id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return chat


@router.post("/{chat_id}/messages", response_model=MessageSchema)
async def create_message(
    *,
    db: AsyncSession = Depends(get_db),
    chat_id: int,
    message_in: MessageCreate,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Create new message in chat."""
    # Verify chat belongs to user
    chat = await chat_service.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    message = await message_service.create_with_chat(
        db=db, obj_in=message_in, chat_id=chat_id
    )
    return message


@router.get("/{chat_id}/messages", response_model=List[MessageSchema])
async def read_messages(
    *,
    db: AsyncSession = Depends(get_db),
    chat_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get messages for a chat."""
    # Verify chat belongs to user
    chat = await chat_service.get(db=db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")

    messages = await message_service.get_by_chat(
        db=db, chat_id=chat_id, skip=skip, limit=limit
    )
    return messages
