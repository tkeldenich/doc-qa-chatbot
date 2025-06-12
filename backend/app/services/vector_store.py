import os
import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Where
from langchain.schema import Document

from app.core.config import settings

# Type aliases for better readability
EmbeddingType = Union[Sequence[float], Sequence[int]]
MetadataType = Mapping[str, Union[str, int, float, bool, None]]


class VectorStoreService:
    def __init__(self) -> None:
        self._client: Optional[ClientAPI] = None
        self._collection: Optional[Collection] = None

    def _get_client(self) -> ClientAPI:
        """Initialize ChromaDB client."""
        if self._client is None:
            # Ensure the ChromaDB directory exists
            chroma_path = os.path.abspath(settings.CHROMADB_PATH)
            os.makedirs(chroma_path, exist_ok=True)

            # Use PersistentClient for better reliability
            self._client = chromadb.PersistentClient(path=chroma_path)
            print(f"✅ ChromaDB client initialized at: {chroma_path}")

        # At this point, _client should not be None
        assert self._client is not None
        return self._client

    def _get_collection(
        self, collection_name: str = "documents"
    ) -> Collection:
        """Get or create ChromaDB collection - simplified approach"""
        if self._collection is not None:
            return self._collection

        client = self._get_client()

        try:
            # Always try to create the collection first
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Document chunks for Q&A chatbot"},
            )
            print(f"✅ ChromaDB collection ready: {collection_name}")

        except Exception as e:
            print(f"❌ Error with collection: {e}")
            # If that fails, try to reset and create
            try:
                client.delete_collection(collection_name)
                print(f"🗑️ Deleted existing collection: {collection_name}")
            except Exception as delete_error:
                # Log the deletion error but continue
                print(f"⚠️ Could not delete collection: {delete_error}")

            try:
                self._collection = client.create_collection(
                    name=collection_name,
                    metadata={
                        "description": "Document chunks for Q&A chatbot"
                    },
                )
                print(f"✅ Created new collection: {collection_name}")
            except Exception as e2:
                raise Exception(f"Failed to create ChromaDB collection: {e2}")

        return self._collection

    async def add_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Add documents to vector store."""
        collection = self._get_collection()

        # Generate unique IDs for each chunk
        chunk_ids = [str(uuid.uuid4()) for _ in documents]

        # Prepare metadata for each document
        metadatas: List[MetadataType] = []
        for i, doc in enumerate(documents):
            doc_metadata = doc.metadata.copy() if doc.metadata else {}
            if metadata:
                doc_metadata.update(metadata)

            # ChromaDB requires simple metadata
            sanitized_metadata = self._sanitize_metadata(doc_metadata)
            metadatas.append(sanitized_metadata)

        # Convert embeddings to the expected format
        embedding_array: List[EmbeddingType] = [
            [float(x) for x in embedding] for embedding in embeddings
        ]

        # Add to ChromaDB
        try:
            collection.add(
                ids=chunk_ids,
                documents=[doc.page_content for doc in documents],
                embeddings=embedding_array,
                metadatas=metadatas,
            )
            print(f"✅ Added {len(chunk_ids)} chunks to ChromaDB")
        except Exception as e:
            print(f"❌ Error adding to ChromaDB: {e}")
            raise

        return chunk_ids

    async def similarity_search(
        self,
        query_embedding: List[float],
        filter_metadata: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        collection = self._get_collection()

        # Prepare where clause for filtering
        where_clause: Optional[Where] = None
        if filter_metadata:
            # Convert to Where type (only simple types, no None values)
            where_dict: Dict[str, Union[str, int, float, bool]] = {}
            for key, value in filter_metadata.items():
                if (
                    isinstance(value, (str, int, float, bool))
                    and value is not None
                ):
                    where_dict[key] = value
                elif value is not None:
                    where_dict[key] = str(value)

            # Cast to Where type if we have any conditions
            if where_dict:
                where_clause = cast(Where, where_dict)

        # Convert query embedding to expected format
        query_embedding_typed: EmbeddingType = [
            float(x) for x in query_embedding
        ]

        try:
            # Perform similarity search
            results = collection.query(
                query_embeddings=[query_embedding_typed],
                n_results=min(
                    top_k, collection.count()
                ),  # Don't ask for more than we have
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            print(f"❌ Error querying ChromaDB: {e}")
            return []

        # Check if we got any results
        if not results["documents"] or not results["documents"][0]:
            print("ℹ️ No documents found in ChromaDB")
            return []

        # Format results with proper type handling
        formatted_results = []
        documents = results["documents"]
        ids = results["ids"]
        metadatas = results["metadatas"]
        distances = results["distances"]

        if documents and ids and metadatas and distances:
            for i in range(len(documents[0])):
                formatted_results.append(
                    {
                        "id": ids[0][i],
                        "content": documents[0][i],
                        "metadata": metadatas[0][i] or {},
                        "similarity_score": 1
                        - distances[0][i],  # Convert distance to similarity
                    }
                )

        return formatted_results

    async def delete_document(self, document_id: int) -> bool:
        """Delete all chunks for a document."""
        collection = self._get_collection()

        try:
            # Find all chunks for this document
            where_condition = cast(Where, {"document_id": str(document_id)})
            results = collection.get(where=where_condition)

            if results["ids"]:
                collection.delete(ids=results["ids"])
                print(
                    f"✅ Deleted {len(results['ids'])} chunks for document "
                    f"{document_id}"
                )
                return True

        except Exception as e:
            print(f"❌ Error deleting document {document_id}: {e}")
            return False

        return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        try:
            collection = self._get_collection()
            count = collection.count()

            return {
                "total_chunks": count,
                "collection_name": collection.name,
                "status": "healthy",
            }
        except Exception as e:
            return {
                "total_chunks": 0,
                "collection_name": "documents",
                "status": f"error: {e}",
            }

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> MetadataType:
        """Sanitize metadata for ChromaDB storage."""
        sanitized: Dict[str, Union[str, int, float, bool, None]] = {}

        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            else:
                # Convert complex types to strings
                sanitized[key] = str(value)

        return sanitized


vector_store_service = VectorStoreService()
