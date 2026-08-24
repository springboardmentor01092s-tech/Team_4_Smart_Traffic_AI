"""
app/core/config.py

Centralized configuration management using Pydantic BaseSettings.
All settings are loaded from environment variables (or .env file).

Extension point: Future modules may add their own settings classes
that inherit from or compose with Settings.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All fields are typed and validated by Pydantic v2.
    Add new settings as class attributes; they are automatically
    pulled from .env or the process environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars (safe for multi-module .env)
    )

    # ─── Application ─────────────────────────────────────────────────────────
    app_name: str = Field(default="TrafficVision AI", description="Human-readable app name")
    app_version: str = Field(default="1.0.0", description="Semantic version string")
    app_env: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=False, description="Enable debug mode (never True in prod)")

    # ─── API ─────────────────────────────────────────────────────────────────
    api_v1_prefix: str = Field(default="/api/v1", description="URL prefix for v1 API routes")

    # ─── Database ────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/trafficvision",
        description="Async PostgreSQL connection string (asyncpg driver)",
    )

    # ─── JWT ─────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key for signing JWTs. Must be at least 32 chars.",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        gt=0,
        description="Number of minutes before an access token expires",
    )

    # ─── CORS ────────────────────────────────────────────────────────────────
    allowed_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # ─── Logging ─────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity level",
    )

    # ─── Analytics (Milestone 3) ─────────────────────────────────────────────
    trend_increasing_threshold_percent: float = Field(
        default=5.0,
        ge=0.0,
        description="Percentage threshold above which a trend is considered INCREASING.",
    )
    trend_decreasing_threshold_percent: float = Field(
        default=-5.0,
        le=0.0,
        description="Percentage threshold below which a trend is considered DECREASING.",
    )

    # ─── Maps / Routing (Milestone 2) ─────────────────────────────────────────
    maps_provider_url: str = Field(
        default="http://router.project-osrm.org",
        description="Base URL for the external routing/maps provider (OSRM).",
    )
    maps_api_key: str = Field(
        default="",
        description="API key for the maps provider. Empty string = no key (OSRM public server).",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str) -> str:
        """Validate and strip comma-separated origins string."""
        if not isinstance(v, str):
            raise ValueError("allowed_origins must be a string")
        return v.strip()

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a Python list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """True when running in development environment."""
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using lru_cache ensures the .env file is read only once
    and the same Settings object is reused across the application.

    Usage:
        from app.core.config import get_settings
        settings = get_settings()
    """
    return Settings()


# Module-level singleton for convenience imports
settings: Settings = get_settings()
