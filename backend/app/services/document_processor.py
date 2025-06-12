import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding import embedding_service
from app.services.vector_store import vector_store_service


class DocumentProcessor:
    def __init__(self) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    async def process_document(
        self, db: AsyncSession, document_id: int, file_path: str
    ) -> Dict[str, Any]:
        """Process a document: load, chunk, embed, and store"""
        try:
            # Update status to processing
            await self._update_document_status(db, document_id, "processing")

            # Load document content
            documents = await self._load_document(file_path)

            # Split into chunks
            chunks = self.text_splitter.split_documents(documents)

            # Generate embeddings with OpenAI
            embeddings = await embedding_service.embed_documents(
                [chunk.page_content for chunk in chunks]
            )

            # Store in vector database
            chunk_ids = await vector_store_service.add_documents(
                documents=chunks,
                embeddings=embeddings,
                metadata={"document_id": document_id},
            )

            # Update document status
            await self._update_document_status(
                db, document_id, "completed", chunk_count=len(chunks)
            )

            return {
                "status": "success",
                "chunks_created": len(chunks),
                "chunk_ids": chunk_ids,
            }

        except Exception as e:
            await self._update_document_status(
                db, document_id, "failed", error_message=str(e)
            )
            raise

    async def _load_document(self, file_path: str) -> List[Document]:
        """Load document based on file type."""
        file_ext = Path(file_path).suffix.lower()

        loader: Union[PyPDFLoader, Docx2txtLoader]
        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_ext == ".docx":
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        documents: List[Document] = await asyncio.to_thread(loader.load)
        return documents

    async def _update_document_status(
        self,
        db: AsyncSession,
        document_id: int,
        status: str,
        error_message: Optional[str] = None,
        chunk_count: Optional[int] = None,
    ) -> None:
        """Update document processing status."""
        from app.services.document import document_service

        # First, get the document object
        document = await document_service.get(db, id=document_id)
        if not document:
            raise ValueError(f"Document with id {document_id} not found")

        update_data: Dict[str, Any] = {"processing_status": status}

        if error_message:
            update_data["error_message"] = error_message
        if chunk_count is not None:
            update_data["chunk_count"] = chunk_count  # ✅ Keep as integer
        if status == "completed":
            update_data["processed_at"] = (
                datetime.utcnow()
            )  # ✅ Keep as datetime object

        # Use the document object instead of ID
        await document_service.update(db, db_obj=document, obj_in=update_data)


document_processor: DocumentProcessor = DocumentProcessor()
