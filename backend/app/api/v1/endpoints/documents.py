import hashlib
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.document import Document as DocumentSchema
from app.schemas.document import DocumentCreate
from app.services.document import document_service
from app.services.user import user_service

router = APIRouter()


def create_secure_temp_file(file: UploadFile) -> str:
    """Create a secure temporary file with proper naming and location.

    Returns the path to the temporary file.
    """
    # Get file extension safely
    file_extension = ""
    if file.filename:
        file_extension = Path(file.filename).suffix

        # Validate file extension against allowed types
        if file_extension.lower() not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File type {file_extension} not allowed. "
                    f"Allowed types: {settings.ALLOWED_FILE_TYPES}"
                ),
            )

    # Create a secure temporary file with a random name
    temp_fd, temp_path = tempfile.mkstemp(
        suffix=file_extension, prefix=f"upload_{uuid.uuid4().hex[:8]}_"
    )

    # Close the file descriptor since we'll handle the file ourselves
    os.close(temp_fd)

    return temp_path


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


@router.get("/", response_model=List[DocumentSchema])
async def read_documents(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Retrieve documents for current user."""
    documents = await document_service.get_by_owner(
        db=db, owner_id=current_user.id, skip=skip, limit=limit
    )
    return documents


@router.post("/upload", response_model=DocumentSchema)
async def upload_document(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Upload a new document."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file size
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {
                settings.MAX_FILE_SIZE} bytes",
        )

    # Reset file pointer for re-reading if needed
    await file.seek(0)

    temp_path = None
    try:
        # Create secure temporary file
        temp_path = create_secure_temp_file(file)

        # Save uploaded file to temporary location
        with open(temp_path, "wb") as temp_file:
            temp_file.write(content)

        # Calculate file hash
        content_hash = calculate_file_hash(temp_path)

        # Create document record
        document_in = DocumentCreate(
            filename=file.filename,
            original_filename=file.filename,
            file_path=temp_path,  # Now using secure temp path
            file_size=len(content),
            file_type=file.content_type or "unknown",
            content_hash=content_hash,
        )

        document = await document_service.create_with_owner(
            db=db, obj_in=document_in, owner_id=current_user.id
        )

        return document

    except Exception as e:
        # Clean up temporary file if something goes wrong
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass  # File cleanup failed, but don't mask the original error
        raise e


@router.get("/{document_id}", response_model=DocumentSchema)
async def read_document(
    *,
    db: AsyncSession = Depends(get_db),
    document_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Get document by ID."""
    document = await document_service.get(db=db, id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.owner_id != current_user.id and not user_service.is_superuser(
        current_user
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return document


@router.delete("/{document_id}")
async def delete_document(
    *,
    db: AsyncSession = Depends(get_db),
    document_id: int,
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """Delete a document."""
    document = await document_service.get(db=db, id=document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.owner_id != current_user.id and not user_service.is_superuser(
        current_user
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Clean up file from filesystem
    if document.file_path and os.path.exists(document.file_path):
        try:
            os.unlink(document.file_path)
        except OSError:
            pass  # File cleanup failed, but continue with database deletion

    await document_service.remove(db=db, id=document_id)
    return {"message": "Document deleted successfully"}
