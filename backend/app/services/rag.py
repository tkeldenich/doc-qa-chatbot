from typing import Any, Dict, List, Optional

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import settings
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store_service


class RAGService:
    def __init__(self) -> None:
        self._chat_model: Optional[ChatOpenAI] = None

    def _get_chat_model(self, model_provider: str = "openai") -> ChatOpenAI:
        """Initialize OpenAI chat model."""
        if self._chat_model is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key is required")

            # You can extend this to support different providers
            model_name = settings.MODEL_NAME or "gpt-3.5-turbo"
            if model_provider == "openai":
                # Could add logic for different OpenAI models
                pass
            # Add other providers as needed

            self._chat_model = ChatOpenAI(
                api_key=SecretStr(
                    settings.OPENAI_API_KEY
                ),  # Wrap in SecretStr
                model=model_name,  # Now guaranteed to be str, not str | None
                temperature=0.1,
            )
        return self._chat_model

    async def answer_question(
        self,
        question: str,
        document_ids: Optional[List[int]] = None,
        max_context_chunks: int = 5,
        use_hybrid_search: bool = False,  # Added missing parameter
        model_provider: str = "openai",  # Added missing parameter
    ) -> Dict[str, Any]:
        """Answer a question using RAG approach."""

        # Get relevant context
        context_chunks = await self._retrieve_context(
            question=question,
            document_ids=document_ids,
            max_chunks=max_context_chunks,
            use_hybrid_search=use_hybrid_search,
        )

        if not context_chunks:
            return {
                "answer": "No relevant information to answer your question.",
                "sources": [],
                "context_used": [],
                "metadata": {
                    "model_provider": model_provider,
                    "chunks_used": 0,
                    "use_hybrid_search": use_hybrid_search,
                },
            }

        # Generate answer
        answer = await self._generate_answer(
            question, context_chunks, model_provider
        )

        return {
            "answer": answer,
            "sources": self._format_sources(context_chunks),
            "context_used": [
                chunk["content"][:200] + "..." for chunk in context_chunks
            ],
            "metadata": {
                "model_provider": model_provider,
                "chunks_used": len(context_chunks),
                "use_hybrid_search": use_hybrid_search,
            },
        }

    async def _retrieve_context(
        self,
        question: str,
        document_ids: Optional[List[int]] = None,
        max_chunks: int = 5,
        use_hybrid_search: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context using vector search."""

        # Get query embedding
        query_embedding = await embedding_service.embed_query(question)

        # Search for similar chunks
        results = await vector_store_service.similarity_search(
            query_embedding=query_embedding,
            filter_metadata=(
                {"document_id": document_ids[0]} if document_ids else None
            ),
            top_k=max_chunks,
        )

        return [
            {
                "content": result["content"],
                "chunk_id": result["id"],
                "score": result["similarity_score"],
                "metadata": result["metadata"],
            }
            for result in results
        ]

    async def _generate_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        model_provider: str = "openai",
    ) -> str:
        """Generate answer using OpenAI."""

        # Prepare context
        context_text = "\n\n".join(
            [
                f"Context {i+1}: {chunk['content']}"
                for i, chunk in enumerate(context_chunks)
            ]
        )

        # Create prompt
        system_prompt = """
You are a helpful assistant that answers questions based on the
provided context.

Use only the information from the context to answer questions.
If the context doesn't contain enough information, say so clearly.
Be concise but comprehensive."""

        user_prompt = f"""Context:
{context_text}

Question: {question}

Answer:"""

        # Generate response
        chat_model = self._get_chat_model(model_provider)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await chat_model.ainvoke(messages)

        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, list):
            # Handle case where content might be a list
            return " ".join(str(item) for item in response.content)
        else:
            return str(response.content)

    def _format_sources(
        self, context_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format source information."""
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["metadata"].get("document_id"),
                "score": chunk["score"],
                "preview": chunk["content"][:150] + "...",
            }
            for chunk in context_chunks
        ]


rag_service: RAGService = RAGService()
