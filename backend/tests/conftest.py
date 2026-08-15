"""
Pytest configuration and shared fixtures.

IMPORTANT — Execution order:
  conftest.py is loaded before any test module is imported.
  We use this to set required environment variables BEFORE Pydantic Settings
  parses them. If environment variables are set after import, the cached
  Settings instance will not pick them up.

Test strategy:
  - Unit tests: Pure Python, no I/O, no database, no network
  - Integration tests: Require live PostgreSQL (marked with @pytest.mark.integration)
  - API tests: Use httpx.AsyncClient with ASGITransport (no live server)

Why ASGITransport?
  It calls the FastAPI app in-process without binding a real TCP socket.
  Tests are fast (<1ms overhead per request) and require no port management.

Adding new fixtures:
  - Fixtures used by a single test module: define them in that module
  - Fixtures used by multiple modules: define them here
  - Fixtures requiring a database: mark them @pytest.mark.integration
    and guard with: pytest.importorskip("asyncpg")
"""

import os

# ── Set test environment variables BEFORE any app imports ────────────────────
# These override .env so tests never depend on a developer's local .env file.
# Keep these minimal — test only what the test needs.
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-for-pytest-suite-minimum-32-characters-long",
)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/test_knowledge_platform",
)
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")  # Suppress logs during tests
os.environ.setdefault("LOG_FORMAT", "console")
os.environ.setdefault("DATABASE_ECHO", "false")
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")
os.environ.setdefault("DATABASE_AUTO_CREATE", "true")

# ── Clear the lru_cache so test settings take effect ─────────────────────────
from app.config.settings import get_settings

get_settings.cache_clear()

# ── Standard imports ──────────────────────────────────────────────────────────
from collections.abc import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.dependencies import get_storage_gateway
from app.main import app  # noqa: E402
from app.services.storage import InMemoryStorageGateway

# Share one mock gateway per test session
_mock_storage = InMemoryStorageGateway()
app.dependency_overrides[get_storage_gateway] = lambda: _mock_storage

@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client scoped to a test module.

    Uses ASGITransport to call the FastAPI app in-process — no real HTTP server.
    Module-scoped to reuse the client across tests in the same file,
    while still triggering lifespan events once per module.
    """
    try:
        from asgi_lifespan import LifespanManager
        async with LifespanManager(app), AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
    except ImportError:
        # Fallback if asgi_lifespan not installed: trigger manually
        from app.database.engine import engine, initialize_database
        await initialize_database()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac
        await engine.dispose()
