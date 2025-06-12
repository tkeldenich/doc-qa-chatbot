from typing import Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/services")
async def health_services() -> Dict[str, str]:
    """Check health of all services."""
    health_status = {
        "database": "unknown",
        "vector_store": "unknown",
        "elasticsearch": "unknown",
        "embedding_service": "unknown",
    }

    try:
        # Check vector store
        from app.services.vector_store import vector_store_service

        await vector_store_service.get_collection_stats()
        health_status["vector_store"] = "healthy"
    except Exception as e:
        health_status["vector_store"] = f"error: {str(e)}"

    try:
        # Check Elasticsearch
        from app.services.elasticsearch_service import elasticsearch_service

        await elasticsearch_service.get_index_stats()
        health_status["elasticsearch"] = "healthy"
    except Exception as e:
        health_status["elasticsearch"] = f"error: {str(e)}"

    try:
        # Check embedding service
        from app.services.embedding import embedding_service

        await embedding_service.embed_query("test")
        health_status["embedding_service"] = "healthy"
    except Exception as e:
        health_status["embedding_service"] = f"error: {str(e)}"

    return health_status
