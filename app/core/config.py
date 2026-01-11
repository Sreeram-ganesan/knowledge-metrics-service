"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",  # This tells Pydantic to load a .env file if present
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=True,  # ← Best practice for config objects
    )

    # Application
    app_name: str = "Knowledge & Metrics Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Environment
    environment: Literal["development", "production", "testing"] = "development"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    # Data paths
    data_dir: Path = Path(__file__).parent.parent.parent / "data"
    csv_filename: str = "vendor_metrics.csv"

    # API settings
    api_prefix: str = "/api/v1"

    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    @property
    def effective_log_level(self) -> str:
        """Return DEBUG if debug mode, otherwise configured log_level."""
        return "DEBUG" if self.debug else self.log_level

    @property
    def effective_log_format(self) -> str:
        """Return json for production, otherwise configured log_format."""
        if self.environment == "production":
            return "json"
        return self.log_format

    @property
    def csv_path(self) -> Path:
        """Full path to the vendor metrics CSV file."""
        return self.data_dir / self.csv_filename


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()
