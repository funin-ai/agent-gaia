"""Repository for LLM model cost data from database."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.core.database import get_db_pool
from src.utils.logger import logger


@dataclass
class ModelCostInfo:
    """Model cost information from database."""
    provider: str
    model_name: str
    model_family: Optional[str]
    input_cost_per_mtok: Decimal
    output_cost_per_mtok: Decimal
    is_active: bool

    @property
    def input_cost_per_1k(self) -> float:
        """Get input cost per 1K tokens (convert from MTok).

        Returns:
            Cost per 1K tokens in USD
        """
        # MTok = per million tokens, so divide by 1000 to get per 1K tokens
        return float(self.input_cost_per_mtok) / 1000

    @property
    def output_cost_per_1k(self) -> float:
        """Get output cost per 1K tokens (convert from MTok).

        Returns:
            Cost per 1K tokens in USD
        """
        # MTok = per million tokens, so divide by 1000 to get per 1K tokens
        return float(self.output_cost_per_mtok) / 1000


class ModelCostRepository:
    """Repository for accessing model cost data from database."""

    # Cache for model costs (model_name -> ModelCostInfo)
    _cache: dict[str, ModelCostInfo] = {}
    _cache_loaded: bool = False

    @classmethod
    async def get_cost_by_model(cls, model_name: str) -> Optional[ModelCostInfo]:
        """Get cost information for a specific model.

        Args:
            model_name: Model name (e.g., 'claude-opus-4-5-20251101')

        Returns:
            ModelCostInfo or None if not found
        """
        # Check cache first
        if model_name in cls._cache:
            return cls._cache[model_name]

        # Load from database
        try:
            db_pool = get_db_pool()
            async with db_pool.connection() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT provider, model_name, model_family,
                           input_cost_per_mtok, output_cost_per_mtok, is_active
                    FROM llm_model_costs
                    WHERE model_name = $1 AND is_active = true
                    """,
                    model_name
                )

                if row:
                    cost_info = ModelCostInfo(
                        provider=row['provider'],
                        model_name=row['model_name'],
                        model_family=row['model_family'],
                        input_cost_per_mtok=row['input_cost_per_mtok'],
                        output_cost_per_mtok=row['output_cost_per_mtok'],
                        is_active=row['is_active'],
                    )
                    # Update cache
                    cls._cache[model_name] = cost_info
                    return cost_info

        except Exception as e:
            logger.error(f"Failed to fetch model cost for {model_name}: {e}")

        return None

    @classmethod
    async def get_cost_by_provider(cls, provider: str) -> list[ModelCostInfo]:
        """Get all active model costs for a provider.

        Args:
            provider: Provider name (e.g., 'anthropic', 'openai', 'google')

        Returns:
            List of ModelCostInfo
        """
        results = []
        try:
            db_pool = get_db_pool()
            async with db_pool.connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT provider, model_name, model_family,
                           input_cost_per_mtok, output_cost_per_mtok, is_active
                    FROM llm_model_costs
                    WHERE provider = $1 AND is_active = true
                    ORDER BY model_name
                    """,
                    provider
                )

                for row in rows:
                    cost_info = ModelCostInfo(
                        provider=row['provider'],
                        model_name=row['model_name'],
                        model_family=row['model_family'],
                        input_cost_per_mtok=row['input_cost_per_mtok'],
                        output_cost_per_mtok=row['output_cost_per_mtok'],
                        is_active=row['is_active'],
                    )
                    # Update cache
                    cls._cache[row['model_name']] = cost_info
                    results.append(cost_info)

        except Exception as e:
            logger.error(f"Failed to fetch model costs for provider {provider}: {e}")

        return results

    @classmethod
    async def load_all_costs(cls) -> dict[str, ModelCostInfo]:
        """Load all active model costs into cache.

        Returns:
            Dictionary of model_name -> ModelCostInfo
        """
        if cls._cache_loaded:
            return cls._cache

        try:
            db_pool = get_db_pool()
            async with db_pool.connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT provider, model_name, model_family,
                           input_cost_per_mtok, output_cost_per_mtok, is_active
                    FROM llm_model_costs
                    WHERE is_active = true
                    ORDER BY provider, model_name
                    """
                )

                cls._cache.clear()
                for row in rows:
                    cost_info = ModelCostInfo(
                        provider=row['provider'],
                        model_name=row['model_name'],
                        model_family=row['model_family'],
                        input_cost_per_mtok=row['input_cost_per_mtok'],
                        output_cost_per_mtok=row['output_cost_per_mtok'],
                        is_active=row['is_active'],
                    )
                    cls._cache[row['model_name']] = cost_info

                cls._cache_loaded = True
                logger.info(f"Loaded {len(cls._cache)} model costs from database")

        except Exception as e:
            logger.error(f"Failed to load model costs: {e}")

        return cls._cache

    @classmethod
    def clear_cache(cls):
        """Clear the model cost cache."""
        cls._cache.clear()
        cls._cache_loaded = False
        logger.debug("Model cost cache cleared")


# Default fallback cost when database is unavailable
DEFAULT_COST = ModelCostInfo(
    provider="unknown",
    model_name="default",
    model_family=None,
    input_cost_per_mtok=Decimal("10.0"),   # $10 per MTok = $0.01 per 1K
    output_cost_per_mtok=Decimal("30.0"),  # $30 per MTok = $0.03 per 1K
    is_active=True,
)
