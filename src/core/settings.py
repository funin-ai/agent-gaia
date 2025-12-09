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


class LLMConfig(BaseModel):
    """LLM configuration."""
    primary_provider: str = "claude"
    backup_chain: list[str] = ["claude", "openai", "gemini"]
    models: dict[str, str] = {
        "claude": "claude-opus-4-5-20251101",
        "openai": "gpt-5.1",
        "gemini": "gemini-3-pro-preview"
    }
    default_temperature: float = 0.2
    default_max_tokens: int = 8192


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
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

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
            "llm": config_data.get("llm", {}),
            "logging": config_data.get("logging", {}),
        }

        # Resolve environment variables in vault token
        if "vault" in settings_data and "token" in settings_data["vault"]:
            token = settings_data["vault"]["token"]
            if token.startswith("${") and token.endswith("}"):
                env_var = token[2:-1]
                settings_data["vault"]["token"] = os.getenv(env_var, "")

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
