"""RAG (Retrieval-Augmented Generation) service.

Integrates with semantic-search-gw for vector search.
"""

import httpx
from typing import Optional
from dataclasses import dataclass

from src.core.settings import get_settings
from src.utils.logger import logger


@dataclass
class RAGResult:
    """Single RAG search result."""
    id: str
    score: float
    content: str
    metadata: dict


@dataclass
class RAGResponse:
    """RAG search response."""
    success: bool
    results: list[RAGResult]
    query: str
    collection: str
    processing_time_ms: float = 0.0
    error: Optional[str] = None


class RAGService:
    """RAG service for semantic search integration."""

    def __init__(self):
        self.settings = get_settings()
        self.config = self.settings.rag
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> RAGResponse:
        """Search for relevant documents.

        Args:
            query: Search query text
            collection_name: Override collection name from config
            limit: Override search limit from config
            score_threshold: Override score threshold from config

        Returns:
            RAGResponse with search results
        """
        if not self.config.enabled:
            return RAGResponse(
                success=False,
                results=[],
                query=query,
                collection="",
                error="RAG is disabled"
            )

        collection = collection_name or self.config.collection_name
        search_limit = limit or self.config.search_limit
        threshold = score_threshold or self.config.score_threshold

        try:
            response = await self.client.post(
                f"{self.config.search_url}/api/search",
                json={
                    "collection_name": collection,
                    "query_text": query,
                    "limit": search_limit,
                    "score_threshold": threshold,
                }
            )

            if response.status_code != 200:
                logger.error(f"RAG search failed: {response.status_code} - {response.text}")
                return RAGResponse(
                    success=False,
                    results=[],
                    query=query,
                    collection=collection,
                    error=f"Search API error: {response.status_code}"
                )

            data = response.json()

            if not data.get("success"):
                return RAGResponse(
                    success=False,
                    results=[],
                    query=query,
                    collection=collection,
                    error=data.get("error", "Unknown error")
                )

            results = []
            for item in data.get("results", []):
                payload = item.get("payload", {})
                # Extract content from payload (common field names)
                content = (
                    payload.get("content") or
                    payload.get("text") or
                    payload.get("chunk") or
                    payload.get("document") or
                    str(payload)
                )
                results.append(RAGResult(
                    id=item.get("id", ""),
                    score=item.get("score", 0.0),
                    content=content,
                    metadata=payload,
                ))

            logger.info(f"RAG search: query='{query[:50]}...', collection={collection}, results={len(results)}")

            return RAGResponse(
                success=True,
                results=results,
                query=query,
                collection=collection,
                processing_time_ms=data.get("processing_time_ms", 0.0),
            )

        except httpx.TimeoutException:
            logger.error(f"RAG search timeout: {query[:50]}...")
            return RAGResponse(
                success=False,
                results=[],
                query=query,
                collection=collection,
                error="Search timeout"
            )
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return RAGResponse(
                success=False,
                results=[],
                query=query,
                collection=collection,
                error=str(e)
            )

    def format_context(self, results: list[RAGResult], max_chars: int = 4000) -> str:
        """Format RAG results as context for LLM.

        Args:
            results: List of RAG results
            max_chars: Maximum characters for context

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for i, result in enumerate(results, 1):
            entry = f"[문서 {i}] (유사도: {result.score:.2f})\n{result.content}\n"

            if total_chars + len(entry) > max_chars:
                break

            context_parts.append(entry)
            total_chars += len(entry)

        if not context_parts:
            return ""

        return "### 관련 문서\n\n" + "\n".join(context_parts)


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create global RAG service instance."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
