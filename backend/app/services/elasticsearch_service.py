from typing import Any, Dict, List, Optional

from elasticsearch import AsyncElasticsearch
from langchain.schema import Document

from app.core.config import settings


class ElasticsearchService:
    def __init__(self) -> None:
        self._client: Optional[AsyncElasticsearch] = None
        self.index_name = "document_chunks"

    def _get_client(self) -> AsyncElasticsearch:
        """Initialize Elasticsearch client."""
        if self._client is None:
            self._client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
        return self._client

    async def initialize_index(self) -> None:
        """Create index with proper mapping."""
        client = self._get_client()

        # Check if index exists
        if await client.indices.exists(index=self.index_name):
            return

        # Create index with mapping
        mapping = {
            "mappings": {
                "properties": {
                    "content": {"type": "text", "analyzer": "standard"},
                    "document_id": {"type": "integer"},
                    "chunk_id": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "metadata": {"type": "object", "enabled": False},
                    "created_at": {"type": "date"},
                }
            },
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        }

        await client.indices.create(index=self.index_name, body=mapping)

    async def index_document_chunks(
        self, document_id: int, chunks: List[Document], chunk_ids: List[str]
    ) -> None:
        """Index document chunks for keyword search."""
        client = self._get_client()
        await self.initialize_index()

        # Prepare bulk indexing data
        bulk_data: List[Dict[str, Any]] = []

        for i, (chunk, chunk_id) in enumerate(zip(chunks, chunk_ids)):
            doc = {
                "content": chunk.page_content,
                "document_id": document_id,
                "chunk_id": chunk_id,
                "chunk_index": i,
                "metadata": chunk.metadata,
                "created_at": "now",
            }

            bulk_data.append(
                {"index": {"_index": self.index_name, "_id": chunk_id}}
            )
            bulk_data.append(doc)

        # Bulk index
        if bulk_data:
            await client.bulk(body=bulk_data)

    async def search_chunks(
        self, query: str, document_id: Optional[int] = None, size: int = 10
    ) -> List[Dict[str, Any]]:
        """Search chunks using keyword search."""
        client = self._get_client()

        # Build search query
        search_body: Dict[str, Any] = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                            }
                        }
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "content": {"fragment_size": 150, "number_of_fragments": 3}
                }
            },
            "size": size,
        }

        # Add document filter if specified
        if document_id:
            search_body["query"]["bool"]["filter"] = [
                {"term": {"document_id": document_id}}
            ]

        # Execute search
        response = await client.search(index=self.index_name, body=search_body)

        # Format results
        results: List[Dict[str, Any]] = []
        hits = response.get("hits", {}).get("hits", [])

        for hit in hits:
            source = hit.get("_source", {})
            result: Dict[str, Any] = {
                "chunk_id": hit.get("_id", ""),
                "content": source.get("content", ""),
                "document_id": source.get("document_id", 0),
                "chunk_index": source.get("chunk_index", 0),
                "score": hit.get("_score", 0.0),
                "metadata": source.get("metadata", {}),
            }

            # Add highlights if available
            highlight = hit.get("highlight")
            if highlight and isinstance(highlight, dict):
                result["highlights"] = highlight.get("content", [])

            results.append(result)

        return results

    async def delete_document_chunks(self, document_id: int) -> bool:
        """Delete all chunks for a document."""
        client = self._get_client()

        try:
            # Delete by query
            delete_body = {"query": {"term": {"document_id": document_id}}}

            response = await client.delete_by_query(
                index=self.index_name, body=delete_body
            )

            deleted_count = response.get("deleted", 0)
            return isinstance(deleted_count, int) and deleted_count > 0

        except Exception as e:
            print(f"Error deleting chunks for document {document_id}: {e}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        client = self._get_client()

        try:
            stats = await client.indices.stats(index=self.index_name)
            count = await client.count(index=self.index_name)

            # Safely extract nested values
            total_stats = stats.get("_all", {}).get("total", {})
            store_stats = total_stats.get("store", {})
            size_bytes = store_stats.get("size_in_bytes", 0)

            return {
                "total_documents": count.get("count", 0),
                "index_size": size_bytes,
                "index_name": self.index_name,
            }

        except Exception as e:
            return {"error": str(e)}

    async def close(self) -> None:
        """Close the Elasticsearch client."""
        if self._client:
            await self._client.close()


elasticsearch_service = ElasticsearchService()
