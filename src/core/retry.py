"""Rate limit retry logic using tenacity."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging

from src.utils.logger import logger

# Import rate limit exceptions from each provider
try:
    from openai import RateLimitError as OpenAIRateLimitError
except ImportError:
    OpenAIRateLimitError = Exception

try:
    from anthropic import RateLimitError as AnthropicRateLimitError
except ImportError:
    AnthropicRateLimitError = Exception

try:
    from google.api_core.exceptions import ResourceExhausted as GoogleRateLimitError
except ImportError:
    GoogleRateLimitError = Exception


# Combined rate limit exceptions
RATE_LIMIT_EXCEPTIONS = (
    OpenAIRateLimitError,
    AnthropicRateLimitError,
    GoogleRateLimitError,
)


def create_llm_retry(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 60,
    multiplier: int = 1
):
    """Create a retry decorator for LLM API calls.
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Exponential backoff multiplier
    Returns:
        Retry decorator
    """
    return retry(
        retry=retry_if_exception_type(RATE_LIMIT_EXCEPTIONS),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        stop=stop_after_attempt(max_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG),
        reraise=True
    )


# Default retry decorator
llm_retry = create_llm_retry()


# Async-compatible retry decorator
async_llm_retry = create_llm_retry()
