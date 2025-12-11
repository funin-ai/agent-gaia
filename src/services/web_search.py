"""Web search service for RAG functionality."""

import re
from dataclasses import dataclass
from typing import Optional

from duckduckgo_search import DDGS

from src.utils.logger import logger


@dataclass
class SearchResult:
    """Single web search result."""
    title: str
    url: str
    snippet: str


@dataclass
class WebSearchResponse:
    """Web search response with multiple results."""
    query: str
    results: list[SearchResult]
    has_results: bool

    def to_context(self, max_results: int = 5) -> str:
        """Convert search results to context string for RAG.

        Args:
            max_results: Maximum number of results to include

        Returns:
            Formatted context string
        """
        if not self.results:
            return f"웹 검색 결과가 없습니다: '{self.query}'"

        context_parts = [f"## 웹 검색 결과: '{self.query}'\n"]

        for i, result in enumerate(self.results[:max_results], 1):
            context_parts.append(
                f"### [{i}] {result.title}\n"
                f"- URL: {result.url}\n"
                f"- 내용: {result.snippet}\n"
            )

        context_parts.append(
            "\n---\n"
            "위 검색 결과를 참고하여 사용자의 질문에 답변해주세요. "
            "검색 결과의 출처(URL)를 함께 제공해주세요."
        )

        return "\n".join(context_parts)


# Search intent detection patterns
SEARCH_INTENT_PATTERNS = [
    # Korean patterns
    r"웹\s*서칭|웹\s*검색",
    r"검색\s*해\s*줘|검색\s*해줘",
    r"찾아\s*줘|찾아줘",
    r"인터넷에서|온라인에서",
    r"최신\s*정보|최근\s*뉴스",
    r"~에\s*대해\s*검색",
    # English patterns
    r"(?:web\s*)?search\s+(?:for|about)",
    r"look\s*up|find\s+(?:information|info)\s+(?:about|on)",
    r"search\s+the\s+(?:web|internet)",
    r"google\s+(?:it|this|that)",
]

# Compiled regex for performance
SEARCH_INTENT_REGEX = re.compile(
    "|".join(SEARCH_INTENT_PATTERNS),
    re.IGNORECASE
)


def detect_search_intent(message: str) -> tuple[bool, Optional[str]]:
    """Detect if message contains search intent.

    Args:
        message: User message

    Returns:
        Tuple of (has_search_intent, extracted_query)
    """
    # Check for search intent patterns
    if not SEARCH_INTENT_REGEX.search(message):
        return False, None

    # Extract the actual search query
    # Remove the search command part and get the actual query
    query = message

    # Remove Korean search commands
    query = re.sub(r"웹\s*서칭\s*해\s*줘\.?\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"웹\s*검색\s*해\s*줘\.?\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"검색\s*해\s*줘\.?\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"찾아\s*줘\.?\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"인터넷에서\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"온라인에서\s*", "", query, flags=re.IGNORECASE)

    # Remove English search commands
    query = re.sub(r"(?:web\s*)?search\s+(?:for|about)\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"look\s*up\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"find\s+(?:information|info)\s+(?:about|on)\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"search\s+the\s+(?:web|internet)\s+(?:for)?\s*", "", query, flags=re.IGNORECASE)
    query = re.sub(r"google\s+", "", query, flags=re.IGNORECASE)

    query = query.strip()

    # If query is too short after extraction, use original message
    if len(query) < 2:
        query = message

    return True, query


class WebSearchService:
    """Web search service using DuckDuckGo."""

    def __init__(self, max_results: int = 5, region: str = "kr-kr"):
        """Initialize web search service.

        Args:
            max_results: Maximum number of search results
            region: Search region (kr-kr for Korean results)
        """
        self.max_results = max_results
        self.region = region

    async def search(self, query: str) -> WebSearchResponse:
        """Perform web search.

        Args:
            query: Search query

        Returns:
            WebSearchResponse with search results
        """
        try:
            logger.info(f"Performing web search: '{query}'")

            with DDGS() as ddgs:
                raw_results = list(ddgs.text(
                    query,
                    region=self.region,
                    max_results=self.max_results
                ))

            results = []
            for r in raw_results:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", r.get("link", "")),
                    snippet=r.get("body", r.get("snippet", ""))
                ))

            logger.info(f"Web search completed: {len(results)} results")

            return WebSearchResponse(
                query=query,
                results=results,
                has_results=len(results) > 0
            )

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return WebSearchResponse(
                query=query,
                results=[],
                has_results=False
            )

    async def search_news(self, query: str) -> WebSearchResponse:
        """Search for news articles.

        Args:
            query: Search query

        Returns:
            WebSearchResponse with news results
        """
        try:
            logger.info(f"Performing news search: '{query}'")

            with DDGS() as ddgs:
                raw_results = list(ddgs.news(
                    query,
                    region=self.region,
                    max_results=self.max_results
                ))

            results = []
            for r in raw_results:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", r.get("link", "")),
                    snippet=r.get("body", r.get("excerpt", ""))
                ))

            logger.info(f"News search completed: {len(results)} results")

            return WebSearchResponse(
                query=query,
                results=results,
                has_results=len(results) > 0
            )

        except Exception as e:
            logger.error(f"News search failed: {e}")
            return WebSearchResponse(
                query=query,
                results=[],
                has_results=False
            )


# Global service instance
_web_search_service: Optional[WebSearchService] = None


def get_web_search_service() -> WebSearchService:
    """Get or create global web search service instance.

    Returns:
        WebSearchService instance
    """
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
