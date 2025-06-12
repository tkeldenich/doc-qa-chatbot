from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.chat import (
    Chat,
    ChatCreate,
    DeleteResponse,
    MessageCreate,
    QuestionRequest,
    QuestionResponse,
)
from app.services.chat import chat_service  # Add message service import
from app.services.chat import (
    message_service,
)
from app.services.rag import rag_service

router = APIRouter()


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(
    request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> QuestionResponse:
    """Ask a question using RAG."""

    # Get or create chat session
    chat = None
    if request.chat_id:
        chat_model = await chat_service.get(db, id=request.chat_id)
        if not chat_model or chat_model.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Chat not found")
        chat = chat_model
    else:
        # Create new chat
        chat_data = ChatCreate(title=request.question[:50] + "...")
        chat = await chat_service.create_with_user(
            db, obj_in=chat_data, user_id=current_user.id
        )

    # Save user message
    user_message_data = MessageCreate(content=request.question, role="user")
    await message_service.create_with_chat(
        db, obj_in=user_message_data, chat_id=chat.id
    )

    try:
        # Generate answer using RAG
        rag_response = await rag_service.answer_question(
            question=request.question,
            document_ids=request.document_ids,
            use_hybrid_search=request.use_hybrid_search,
            model_provider=request.model_provider,
        )
        """
        Save assistant message:
        Use create_with_chat instead of create_message
        """
        assistant_message_data = MessageCreate(
            content=rag_response["answer"],
            role="assistant",
            sources=rag_response["sources"],
            chat_metadata=rag_response["metadata"],
        )
        assistant_message = await message_service.create_with_chat(
            db, obj_in=assistant_message_data, chat_id=chat.id
        )

        return QuestionResponse(
            chat_id=chat.id,
            question=request.question,
            answer=rag_response["answer"],
            sources=rag_response["sources"],
            context_used=rag_response["context_used"],
            metadata=rag_response["metadata"],
            message_id=assistant_message.id,
        )

    except Exception as e:
        """
        Save error message:
        Use create_with_chat instead of create_messag
        """
        error_message_data = MessageCreate(
            content=(
                f"I encountered an error processing your question: {str(e)}"
            ),
            role="assistant",
            chat_metadata={"error": True, "error_message": str(e)},
        )
        await message_service.create_with_chat(
            db, obj_in=error_message_data, chat_id=chat.id
        )

        raise HTTPException(
            status_code=500, detail=f"Error processing question: {str(e)}"
        )


@router.get("/", response_model=List[Chat])
async def list_chats(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Chat]:
    """List user's chats."""
    chat_models = await chat_service.get_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    # Convert SQLAlchemy models to Pydantic schemas
    return [Chat.from_orm(chat) for chat in chat_models]


@router.get("/{chat_id}", response_model=Chat)
async def get_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Chat:
    """Get chat with messages."""
    chat_model = await chat_service.get_with_messages(db, chat_id=chat_id)
    if not chat_model:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat_model.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Convert SQLAlchemy model to Pydantic schema
    return Chat.from_orm(chat_model)


@router.delete("/{chat_id}", response_model=DeleteResponse)
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DeleteResponse:
    """Delete a chat."""
    chat = await chat_service.get(db, id=chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await chat_service.remove(db, id=chat_id)
    return DeleteResponse(message="Chat deleted successfully")
