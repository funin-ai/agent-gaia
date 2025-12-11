"""LLM Router with backup chain support."""

from typing import Optional, AsyncIterator
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from src.core.settings import Settings, get_settings
from src.core.retry import llm_retry
from src.utils.logger import logger


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    model: str
    client_class: type
    api_key_name: str
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "claude": ProviderConfig(
        model="claude-opus-4-5-20251101",
        client_class=ChatAnthropic,
        api_key_name="anthropic",
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075
    ),
}


class LLMRouter:
    """Router for multiple LLM providers with backup chain support."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize LLM Router.

        Args:
            settings: Application settings (uses global settings if not provided)
        """
        self.settings = settings or get_settings()
        self.api_keys = self.settings.load_api_keys()
        self.backup_chain = self.settings.llm.backup_chain

        # Update provider configs with settings
        for provider, model in self.settings.llm.models.items():
            if provider in PROVIDER_CONFIGS:
                PROVIDER_CONFIGS[provider].model = model

        logger.info(f"LLM Router initialized with backup chain: {self.backup_chain}")

    def get_llm(
        self,
        provider: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = True,
        use_backup: bool = True
    ) -> BaseChatModel:
        """Get LLM instance for specified provider.

        Args:
            provider: Provider name (claude, openai, gemini)
            model: Optional model override
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            streaming: Enable streaming responses
            use_backup: Try backup providers on failure

        Returns:
            LLM instance

        Raises:
            ValueError: If provider is unknown
            RuntimeError: If all providers fail
        """
        provider = provider.lower()

        if provider not in PROVIDER_CONFIGS:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(PROVIDER_CONFIGS.keys())}"
            )

        try:
            config = PROVIDER_CONFIGS[provider]
            api_key = self.api_keys.get(config.api_key_name)

            if not api_key:
                raise ValueError(f"API key not found for {provider}")

            # Build kwargs based on provider
            kwargs = {
                "model": model or config.model,
                "temperature": temperature or self.settings.llm.default_temperature,
                "max_tokens": max_tokens or self.settings.llm.default_max_tokens,
                "streaming": streaming,
            }

            # Provider-specific API key parameter
            if provider == "gemini":
                kwargs["google_api_key"] = api_key
            else:
                kwargs["api_key"] = api_key

            llm = config.client_class(**kwargs)
            logger.info(f"Created {provider} LLM with model {kwargs['model']}")
            return llm

        except Exception as e:
            logger.error(f"Failed to create {provider} LLM: {e}")
            if use_backup:
                return self._try_backup(provider, model, temperature, max_tokens, streaming)
            raise

    def _try_backup(
        self,
        failed_provider: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = True
    ) -> BaseChatModel:
        """Try backup providers in chain order.

        Args:
            failed_provider: Provider that failed
            model: Optional model override
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            streaming: Enable streaming responses

        Returns:
            LLM instance from backup provider

        Raises:
            RuntimeError: If all backup providers fail
        """
        try:
            idx = self.backup_chain.index(failed_provider)
        except ValueError:
            idx = -1

        for backup in self.backup_chain[idx + 1:]:
            try:
                logger.warning(f"Trying backup provider: {backup}")
                return self.get_llm(
                    backup,
                    model=None,  # Use backup's default model
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=streaming,
                    use_backup=False  # Don't recurse
                )
            except Exception as e:
                logger.error(f"Backup provider {backup} failed: {e}")
                continue

        raise RuntimeError("All backup providers failed")

    @llm_retry
    async def ainvoke(
        self,
        provider: str,
        messages: list[BaseMessage],
        **kwargs
    ) -> BaseMessage:
        """Invoke LLM with retry logic.

        Args:
            provider: Provider name
            messages: List of messages
            **kwargs: Additional arguments for get_llm

        Returns:
            LLM response message
        """
        llm = self.get_llm(provider, **kwargs)
        return await llm.ainvoke(messages)

    @llm_retry
    async def astream(
        self,
        provider: str,
        messages: list[BaseMessage],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream LLM response with retry logic.

        Args:
            provider: Provider name
            messages: List of messages
            **kwargs: Additional arguments for get_llm

        Yields:
            Response chunks
        """
        llm = self.get_llm(provider, streaming=True, **kwargs)
        async for chunk in llm.astream(messages):
            if hasattr(chunk, "content"):
                content = chunk.content
                # Handle Gemini's list content format
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            yield item["text"]
                elif isinstance(content, str) and content:
                    yield content


# Global router instance
_router: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    """Get or create global LLM router instance.

    Returns:
        LLMRouter instance
    """
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
