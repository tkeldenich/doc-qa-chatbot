from typing import List, Optional

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self._embeddings: Optional[OpenAIEmbeddings] = None

    def _get_embeddings(self) -> OpenAIEmbeddings:
        """Initialize OpenAI embeddings."""
        if self._embeddings is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is required")

            self._embeddings = OpenAIEmbeddings(
                api_key=SecretStr(settings.OPENAI_API_KEY),
                model="text-embedding-ada-002",
            )
        return self._embeddings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for documents."""
        embeddings = self._get_embeddings()
        return await embeddings.aembed_documents(texts)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query."""
        embeddings = self._get_embeddings()
        return await embeddings.aembed_query(text)


embedding_service = EmbeddingService()
