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


class TokenCounter:
    """Count tokens and calculate costs."""

    def __init__(self):
        try:
            self._encoding = tiktoken.get_encoding(DEFAULT_ENCODING)
        except Exception:
            self._encoding = None
            logger.warning("tiktoken not available, using approximate counting")

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
        provider: str,
        model: str,
        input_text: str,
        output_text: str,
        messages: Optional[list] = None
    ) -> TokenUsage:
        """Track token usage and calculate costs.

        Args:
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

        # Log usage
        logger.info(
            f"Token usage [{provider}/{model}]: "
            f"in={input_tokens}, out={output_tokens}, total={total_tokens} | "
            f"cost=${total_cost:.6f} (in=${input_cost:.6f}, out=${output_cost:.6f})"
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
