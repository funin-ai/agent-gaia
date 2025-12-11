"""Token counting and cost calculation utilities."""

import tiktoken
from dataclasses import dataclass
from typing import Optional

from src.utils.logger import logger
from src.core.settings import get_settings
from src.core.model_cost_repository import ModelCostRepository, DEFAULT_COST

# Default encoding for token counting
DEFAULT_ENCODING = "cl100k_base"


@dataclass
class TokenUsage:
    """Token usage statistics."""
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float


@dataclass
class SessionUsage:
    """Session-level accumulated usage statistics."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    message_count: int = 0

    def add(self, usage: TokenUsage):
        """Add a single message usage to session totals."""
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_tokens += usage.total_tokens
        self.total_cost += usage.total_cost
        self.message_count += 1

    def reset(self):
        """Reset session statistics."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.message_count = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "message_count": self.message_count,
        }


class TokenCounter:
    """Count tokens and calculate costs."""

    def __init__(self):
        try:
            self._encoding = tiktoken.get_encoding(DEFAULT_ENCODING)
        except Exception:
            self._encoding = None
            logger.warning("tiktoken not available, using approximate counting")

        # Per-session usage tracking (keyed by session_id)
        self._sessions: dict[str, SessionUsage] = {}
        self._last_usage: dict[str, TokenUsage] = {}

    def get_session(self, session_id: str) -> SessionUsage:
        """Get or create session usage statistics."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionUsage()
        return self._sessions[session_id]

    def get_last_usage(self, session_id: str) -> Optional[TokenUsage]:
        """Get last message usage for a session."""
        return self._last_usage.get(session_id)

    def reset_session(self, session_id: str):
        """Reset session usage statistics."""
        if session_id in self._sessions:
            self._sessions[session_id].reset()
        if session_id in self._last_usage:
            del self._last_usage[session_id]
        logger.info(f"Session usage reset: {session_id}")

    def remove_session(self, session_id: str):
        """Remove session when disconnected."""
        self._sessions.pop(session_id, None)
        self._last_usage.pop(session_id, None)
        logger.info(f"Session removed: {session_id}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if not text:
            return 0

        if self._encoding:
            return len(self._encoding.encode(text))

        # Approximate: ~4 chars per token for English, ~2 for Korean
        return len(text) // 3

    def count_messages(self, messages: list) -> int:
        """Count tokens in message list.

        Args:
            messages: List of LangChain messages

        Returns:
            Total token count
        """
        total = 0
        for msg in messages:
            if hasattr(msg, "content"):
                total += self.count_tokens(msg.content)
            # Add overhead for message structure (~4 tokens per message)
            total += 4
        return total

    async def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> tuple[float, float, float]:
        """Calculate cost for token usage from database.

        Args:
            model_name: Model name (e.g., 'claude-opus-4-5-20251101')
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Tuple of (input_cost, output_cost, total_cost)
        """
        # Try to get cost from database
        cost_info = await ModelCostRepository.get_cost_by_model(model_name)

        if cost_info is None:
            # Fallback to config-based costs
            logger.warning(f"Model {model_name} not found in DB, using config fallback")
            return self._calculate_cost_from_config(model_name, input_tokens, output_tokens)

        input_cost = (input_tokens / 1000) * cost_info.input_cost_per_1k
        output_cost = (output_tokens / 1000) * cost_info.output_cost_per_1k
        return input_cost, output_cost, input_cost + output_cost

    def _calculate_cost_from_config(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> tuple[float, float, float]:
        """Fallback: Calculate cost from config file.

        Args:
            model_name: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Tuple of (input_cost, output_cost, total_cost)
        """
        settings = get_settings()

        # Try to find cost by model name in config
        if model_name in settings.llm.costs:
            costs = settings.llm.costs[model_name]
            input_cost = (input_tokens / 1000) * costs.input
            output_cost = (output_tokens / 1000) * costs.output
            return input_cost, output_cost, input_cost + output_cost

        # Ultimate fallback
        input_cost = (input_tokens / 1000) * DEFAULT_COST.input_cost_per_1k
        output_cost = (output_tokens / 1000) * DEFAULT_COST.output_cost_per_1k
        return input_cost, output_cost, input_cost + output_cost

    async def track_usage(
        self,
        session_id: str,
        provider: str,
        model: str,
        input_text: str,
        output_text: str,
        messages: Optional[list] = None
    ) -> TokenUsage:
        """Track token usage and calculate costs.

        Args:
            session_id: Unique session identifier (e.g., websocket connection id)
            provider: Provider name (e.g., 'claude', 'openai', 'gemini')
            model: Model name (e.g., 'claude-opus-4-5-20251101')
            input_text: Input text (user message)
            output_text: Output text (assistant response)
            messages: Optional full message history for context

        Returns:
            TokenUsage with statistics
        """
        # Count input tokens (including history if provided)
        if messages:
            input_tokens = self.count_messages(messages)
        else:
            input_tokens = self.count_tokens(input_text)

        output_tokens = self.count_tokens(output_text)
        total_tokens = input_tokens + output_tokens

        input_cost, output_cost, total_cost = await self.calculate_cost(
            model, input_tokens, output_tokens
        )

        usage = TokenUsage(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )

        # Update session statistics
        self._last_usage[session_id] = usage
        session = self.get_session(session_id)
        session.add(usage)

        # Log usage
        logger.info(
            f"Token usage [{session_id[:8]}][{provider}/{model}]: "
            f"in={input_tokens}, out={output_tokens}, total={total_tokens} | "
            f"cost=${total_cost:.6f} | session: {session.message_count} msgs, ${session.total_cost:.6f}"
        )

        return usage


# Global instance
_counter: Optional[TokenCounter] = None


def get_token_counter() -> TokenCounter:
    """Get or create global token counter."""
    global _counter
    if _counter is None:
        _counter = TokenCounter()
    return _counter
