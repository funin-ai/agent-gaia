"""Application settings with Vault integration."""

import os
from pathlib import Path
from typing import Optional
from functools import lru_cache

import yaml
import hvac
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from src.utils.logger import logger


class VaultConfig(BaseModel):
    """Vault configuration."""
    enabled: bool = False
    url: str = "http://localhost:8201"
    token: str = ""
    secret_path: str = "secret/data/agent-gaia/llm-keys"


class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = "localhost"
    port: int = 5433
    database: str = "funin-ai"
    user: str = "postgres"
    password: str = ""
    min_pool_size: int = 1
    max_pool_size: int = 5

    @property
    def dsn(self) -> str:
        """Get PostgreSQL DSN string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class ModelCost(BaseModel):
    """Cost per 1K tokens (USD)."""
    input: float = 0.01
    output: float = 0.03


class LLMConfig(BaseModel):
    """LLM configuration."""
    primary_provider: str = "claude"
    backup_chain: list[str] = ["claude", "openai", "gemini"]
    models: dict[str, str] = {
        "claude": "claude-opus-4-5-20251101",
        "openai": "gpt-5.1",
        "gemini": "gemini-3-pro-preview"
    }
    # Costs keyed by model name (not provider)
    costs: dict[str, ModelCost] = {
        "claude-opus-4-5-20251101": ModelCost(input=0.015, output=0.075),
        "claude-sonnet-4-20250514": ModelCost(input=0.003, output=0.015),
        "gpt-5.1": ModelCost(input=0.01, output=0.03),
        "gemini-3-pro-preview": ModelCost(input=0.00125, output=0.005),
    }
    default_temperature: float = 0.2
    default_max_tokens: int = 8192

    def get_model_cost(self, provider: str) -> ModelCost:
        """Get cost for a provider's configured model."""
        model_name = self.models.get(provider)
        if model_name and model_name in self.costs:
            return self.costs[model_name]
        # Fallback default
        return ModelCost(input=0.01, output=0.03)


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


class AuthConfig(BaseModel):
    """Authentication configuration."""
    enabled: bool = False
    jwt_secret: str = "change-this-secret-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # OAuth providers
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # Redirect URLs
    frontend_url: str = "http://localhost:9033"
    callback_url: str = "http://localhost:9033/api/v1/auth/{provider}/callback"


class Settings(BaseSettings):
    """Application settings."""

    # App info
    app_name: str = "AgentGaia"
    app_version: str = "0.1.0"
    app_env: str = "local"
    debug: bool = True

    # Sub-configurations
    server: ServerConfig = Field(default_factory=ServerConfig)
    vault: VaultConfig = Field(default_factory=VaultConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)

    # API Keys (loaded from Vault or environment)
    _api_keys: Optional[dict[str, str]] = None

    class Config:
        env_prefix = ""
        env_nested_delimiter = "__"

    @classmethod
    def from_yaml(cls, env: str = "local") -> "Settings":
        """Load settings from YAML config file.

        Args:
            env: Environment name (local, dev, prod)

        Returns:
            Settings instance
        """
        config_path = Path(__file__).parent.parent.parent / "config" / f"config-{env}.yml"

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return cls()

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Flatten app config
        app_config = config_data.get("app", {})

        settings_data = {
            "app_name": app_config.get("name", "AgentGaia"),
            "app_version": app_config.get("version", "0.1.0"),
            "app_env": app_config.get("env", env),
            "debug": app_config.get("debug", True),
            "server": config_data.get("server", {}),
            "vault": config_data.get("vault", {}),
            "database": config_data.get("database", {}),
            "llm": config_data.get("llm", {}),
            "logging": config_data.get("logging", {}),
            "auth": config_data.get("auth", {}),
        }

        # Resolve environment variables in vault token
        if "vault" in settings_data and "token" in settings_data["vault"]:
            token = settings_data["vault"]["token"]
            if token.startswith("${") and token.endswith("}"):
                env_var = token[2:-1]
                settings_data["vault"]["token"] = os.getenv(env_var, "")

        # Resolve environment variables in database password
        if "database" in settings_data and "password" in settings_data["database"]:
            password = settings_data["database"]["password"]
            if password.startswith("${") and password.endswith("}"):
                env_var = password[2:-1]
                settings_data["database"]["password"] = os.getenv(env_var, "")

        # Resolve environment variables in auth config
        if "auth" in settings_data:
            auth_config = settings_data["auth"]
            for key in ["google_client_id", "google_client_secret",
                        "github_client_id", "github_client_secret", "jwt_secret"]:
                if key in auth_config:
                    value = auth_config[key]
                    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                        env_var = value[2:-1]
                        auth_config[key] = os.getenv(env_var, "")

        return cls(**settings_data)

    def load_api_keys(self) -> dict[str, str]:
        """Load API keys from Vault or environment variables.

        Returns:
            Dictionary of provider -> API key
        """
        if self._api_keys is not None:
            return self._api_keys

        if self.vault.enabled and self.vault.token:
            try:
                client = hvac.Client(url=self.vault.url, token=self.vault.token)

                if not client.is_authenticated():
                    logger.error("Vault authentication failed")
                    return self._load_from_env()

                # Read secrets from Vault
                secret_path = self.vault.secret_path.replace("secret/data/", "")
                response = client.secrets.kv.v2.read_secret_version(
                    path=secret_path,
                    mount_point="secret"
                )

                if response and "data" in response:
                    data = response["data"]["data"]
                    self._api_keys = {
                        "anthropic": data.get("anthropic", "") or data.get("ANTHROPIC_API_KEY", ""),
                        "openai": data.get("openai", "") or data.get("OPENAI_API_KEY", ""),
                        "google": data.get("google", "") or data.get("GOOGLE_API_KEY", ""),
                    }
                    logger.info("API keys loaded from Vault")
                    return self._api_keys

            except Exception as e:
                logger.error(f"Failed to load API keys from Vault: {e}")

        return self._load_from_env()

    def _load_from_env(self) -> dict[str, str]:
        """Load API keys from environment variables.

        Returns:
            Dictionary of provider -> API key
        """
        self._api_keys = {
            "anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "openai": os.getenv("OPENAI_API_KEY", ""),
            "google": os.getenv("GOOGLE_API_KEY", ""),
        }
        logger.info("API keys loaded from environment variables")
        return self._api_keys

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider.

        Args:
            provider: Provider name (anthropic, openai, google)

        Returns:
            API key or None
        """
        keys = self.load_api_keys()
        return keys.get(provider.lower())


@lru_cache()
def get_settings(env: Optional[str] = None) -> Settings:
    """Get cached settings instance.

    Args:
        env: Environment name (defaults to APP_ENV or 'local')

    Returns:
        Settings instance
    """
    if env is None:
        env = os.getenv("APP_ENV", "local")
    return Settings.from_yaml(env)


# Global settings instance
settings = get_settings()
