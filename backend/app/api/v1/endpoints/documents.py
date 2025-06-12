import os
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import Document, DocumentCreate
from app.services.document import document_service
from app.services.document_processor import document_processor
from app.utils.file_utils import (
    generate_file_hash,
    save_uploaded_file,
    validate_file,
)

router = APIRouter()


async def validate_file_wrapper(file: UploadFile) -> Dict[str, Any]:
    """Wrapper for validate_file to ensure proper return type."""
    return await validate_file(file)


@router.post("/upload", response_model=Document)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    """Upload and process a document."""

    # Validate file
    validation_result = await validate_file_wrapper(file)
    if not validation_result["valid"]:
        raise HTTPException(status_code=400, detail=validation_result["error"])

    # Save file
    file_path = await save_uploaded_file(file, current_user.id)

    # Calculate file hash
    file_hash = await generate_file_hash(file_path)

    # Check if document already exists
    existing_doc = await document_service.get_by_hash(
        db, content_hash=file_hash
    )
    if existing_doc:
        # Remove the uploaded file since we already have it
        os.remove(file_path)
        raise HTTPException(
            status_code=409,
            detail="Document already exists",
            headers={"X-Existing-Document-ID": str(existing_doc.id)},
        )

    # Ensure filename is not None
    filename = file.filename or "unknown_file"

    # Create document record
    document_data = DocumentCreate(
        filename=filename,
        original_filename=filename,
        file_path=file_path,
        file_size=validation_result["size"],
        file_type=validation_result["file_type"],
        content_hash=file_hash,
    )

    document = await document_service.create_with_owner(
        db, obj_in=document_data, owner_id=current_user.id
    )

    # Process document in background
    background_tasks.add_task(
        document_processor.process_document, db, document.id, file_path
    )

    # Convert model to schema
    return Document.from_orm(document)


@router.get("/", response_model=List[Document])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[Document]:
    """List user's documents."""
    # Query documents filtered by owner directly
    from app.models.document import Document as DocumentModel

    result = await db.execute(
        select(DocumentModel)
        .filter(DocumentModel.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()

    # Convert models to schemas
    return [Document.from_orm(doc) for doc in documents]


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    """Get document by ID."""
    document = await document_service.get(db, id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Convert model to schema
    return Document.from_orm(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, str]:
    """Delete a document."""
    document = await document_service.get(db, id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # Delete from vector store and elasticsearch in background
    from app.services.elasticsearch_service import elasticsearch_service
    from app.services.vector_store import vector_store_service

    background_tasks.add_task(
        vector_store_service.delete_document, document_id
    )
    background_tasks.add_task(
        elasticsearch_service.delete_document_chunks, document_id
    )

    # Delete file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    # Delete from database
    await document_service.remove(db, id=document_id)

    return {"message": "Document deleted successfully"}


@router.get("/{document_id}/status")
async def get_processing_status(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Get document processing status."""
    document = await document_service.get(db, id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    return {
        "document_id": document.id,
        "status": document.processing_status,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "processed_at": document.processed_at,
    }
