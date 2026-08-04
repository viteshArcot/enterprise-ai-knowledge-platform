"""Tests for the Phase 1 application foundation components."""

import logging
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config.settings import Settings, get_settings
from app.core import dependencies
from app.core import logging as application_logging
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
    register_exception_handlers,
)
from app.models import Base, TimestampMixin, UUIDMixin
from app.repositories import BaseRepository
from app.services import BaseService


def test_settings_accepts_comma_separated_cors_origins() -> None:
    """The documented CORS environment format must load without JSON decoding."""
    settings = Settings(CORS_ORIGINS="http://localhost:3000, https://app.example.com")

    assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://app.example.com"]


def test_settings_rejects_placeholder_secret_key() -> None:
    """The sample secret must never be accepted as a usable credential."""
    with pytest.raises(ValidationError, match="must be replaced"):
        Settings(SECRET_KEY="REPLACE_ME_generate_with_openssl_rand_hex_32")


def test_settings_rejects_debug_in_production() -> None:
    """Production configuration must keep verbose debugging disabled."""
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(ENVIRONMENT="production", DEBUG=True)


def test_get_settings_returns_cached_instance() -> None:
    """Configuration is parsed once per process for consistent dependency injection."""
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()

    assert first is second


@pytest.mark.asyncio
async def test_exception_handlers_return_consistent_error_envelopes() -> None:
    """Domain, validation, and unexpected exceptions use the documented response shape."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("Document", "missing")

    @app.get("/conflict")
    async def raise_conflict() -> None:
        raise ConflictError("Document already exists.", {"field": "name"})

    @app.get("/validation")
    async def validate(value: int) -> dict[str, int]:
        return {"value": value}

    @app.get("/unexpected")
    async def raise_unexpected() -> None:
        raise RuntimeError("unexpected")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        not_found = await client.get("/not-found")
        conflict = await client.get("/conflict")
        validation = await client.get("/validation", params={"value": "invalid"})
        unexpected = await client.get("/unexpected")

    assert not_found.json()["error"]["code"] == "NOT_FOUND"
    assert conflict.json()["error"]["detail"] == {"field": "name"}
    assert validation.status_code == 422
    assert unexpected.json()["error"]["code"] == "INTERNAL_ERROR"


def test_validation_app_error_has_documented_status() -> None:
    """Business-rule validation errors map to the expected 422 status."""
    error = ValidationAppError("Invalid document state.")

    assert error.status_code == 422


def test_logging_configuration_supports_console_and_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both documented logging formats initialize without errors."""
    monkeypatch.setattr(application_logging.settings, "LOG_FORMAT", "console")
    application_logging.configure_logging()
    monkeypatch.setattr(application_logging.settings, "LOG_FORMAT", "json")
    application_logging.configure_logging()

    assert logging.getLogger().level == logging.WARNING





def test_settings_dependency_returns_configured_singleton() -> None:
    """Dependency injection exposes the cached settings object."""
    assert dependencies.get_app_settings() is get_settings()


def test_model_mixins_and_base_are_composable() -> None:
    """ORM base classes can be combined by future Phase 2 models."""

    class ExampleModel(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "example_models"

    assert ExampleModel.__tablename__ == "example_models"


@pytest.mark.asyncio
async def test_repository_base_methods_are_defined_for_implementations() -> None:
    """The abstract repository exposes the complete Phase 2 CRUD contract."""
    entity_id = uuid.uuid4()

    assert await BaseRepository.get_by_id(None, entity_id) is None
    assert await BaseRepository.list(None) is None
    assert await BaseRepository.create(None, object()) is None
    assert await BaseRepository.update(None, entity_id, object()) is None
    assert await BaseRepository.delete(None, entity_id) is None


def test_base_service_initializes_a_structured_logger() -> None:
    """Services inherit a ready-to-use logger from the base class."""
    service = BaseService()

    assert service._logger is not None
