"""
Centralized application configuration.

Uses Pydantic Settings v2 to load, validate, and type-check all configuration
from environment variables and .env files.

Why this approach?
------------------
- Type safety: All settings are validated at startup. The app fails fast if
  required environment variables are missing or malformed — no silent failures
  in production.
- Single source of truth: Every configurable value lives here. No ad-hoc
  os.getenv() scattered across the codebase.
- Documentation: Each field has a docstring-level comment explaining its
  purpose and valid values.
- Testability: lru_cache can be cleared in tests to substitute test settings.

Evolution plan:
---------------
- Phase 2: Add LLM provider keys (OpenAI, Anthropic, Azure OpenAI)
- Phase 2: Add vector database connection settings (Pinecone, Weaviate, pgvector)
- Phase 3: Add Redis cache settings for session management
- Phase 4: Add OAuth / OIDC provider settings
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables.

    All fields without defaults are REQUIRED and will cause the application
    to fail at startup if not provided.
    """

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Silently ignore unknown env vars
    )

    # =========================================================================
    # Application identity
    # =========================================================================

    # Human-readable name shown in OpenAPI docs and log output
    API_TITLE: str = "Enterprise AI Knowledge Platform"

    # Shown in the OpenAPI /docs description area
    API_DESCRIPTION: str = (
        "Production-grade API for enterprise AI-powered knowledge management. "
        "Phase 1: Engineering Foundation."
    )

    # Follows semantic versioning. Increment on breaking changes.
    API_VERSION: str = "0.1.0"

    # =========================================================================
    # Deployment environment
    # =========================================================================

    # Controls log verbosity, docs visibility, and feature flags
    # Values: development | staging | production
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # Enables verbose error responses. MUST be false in production.
    DEBUG: bool = False

    # =========================================================================
    # Security
    # =========================================================================

    # Random secret key used for token signing and CSRF protection.
    # Generate with: openssl rand -hex 32
    # REQUIRED: No default — the app will refuse to start without it.
    SECRET_KEY: str = Field(..., min_length=32)

    # Allowed cross-origin request origins for the frontend.
    # In production, restrict to your frontend domain only.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # =========================================================================
    # Database — PostgreSQL (async via asyncpg)
    # =========================================================================

    # Full async PostgreSQL connection URL.
    # Format: postgresql+asyncpg://user:password@host:port/database
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description="Async PostgreSQL connection string (required).",
    )

    # Number of persistent connections in the pool.
    # Tune based on PostgreSQL max_connections setting.
    DATABASE_POOL_SIZE: int = Field(default=10, ge=1, le=100)

    # Additional connections allowed when pool is exhausted.
    DATABASE_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)

    # Seconds to wait for a connection before raising a timeout error.
    DATABASE_POOL_TIMEOUT: int = Field(default=30, ge=1)

    # Log all SQL queries to stdout. Enable in development only.
    # WARNING: Leaks sensitive data if enabled in production.
    DATABASE_ECHO: bool = False

    # =========================================================================
    # Logging
    # =========================================================================

    # Minimum log level to emit.
    # Values: DEBUG | INFO | WARNING | ERROR | CRITICAL
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # 'json' — structured JSON for log aggregation systems (Datadog, CloudWatch)
    # 'console' — human-readable colored output for local development
    LOG_FORMAT: Literal["json", "console"] = "json"

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """
        Accept CORS_ORIGINS as either a comma-separated string or a list.

        This allows the env var to be set as:
          CORS_ORIGINS=http://localhost:3000,https://app.example.com
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Reject the placeholder value supplied in .env.example."""
        if value.startswith("REPLACE_ME"):
            raise ValueError(
                "SECRET_KEY must be replaced with a securely generated value."
            )
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Enforce the documented production safety constraint for DEBUG."""
        if self.ENVIRONMENT == "production" and self.DEBUG:
            raise ValueError("DEBUG must be false when ENVIRONMENT is production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton settings instance.

    lru_cache ensures environment variables are parsed exactly once per process.
    In tests, call `get_settings.cache_clear()` before overriding env vars.
    """
    return Settings()


# Module-level singleton for use in non-DI contexts (logging setup, etc.)
# Service and route code should prefer using the get_settings() dependency.
settings: Settings = get_settings()
