import hashlib
from pathlib import Path
from typing import Any, Dict

import aiofiles
from fastapi import UploadFile

from app.core.config import settings


async def validate_file(file: UploadFile) -> Dict[str, Any]:
    """Validate uploaded file."""

    # Check if filename exists
    if not file.filename:
        return {"valid": False, "error": "No filename provided"}

    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    await file.seek(0)  # Reset file pointer

    if file_size > settings.MAX_FILE_SIZE:
        return {
            "valid": False,
            "error": "File too large. Maximum size:"
            f"{settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB",
        }

    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        return {
            "valid": False,
            "error": "File type not supported. Allowed types:"
            f"{', '.join(settings.ALLOWED_FILE_TYPES)}",
        }

    return {"valid": True, "size": file_size, "file_type": file_ext}


async def save_uploaded_file(file: UploadFile, user_id: int) -> str:
    """Save uploaded file to disk."""

    # Check if filename exists
    if not file.filename:
        raise ValueError("No filename provided")

    # Create user upload directory
    upload_dir = Path("uploads") / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    import uuid

    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    # Save file
    async with aiofiles.open(file_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)

    return str(file_path)


async def generate_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of file content."""

    hash_sha256 = hashlib.sha256()

    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()
