"""
Dependency injection providers.

FastAPI's Depends() system enables constructor-like DI for route handlers.
Dependencies defined here are the canonical way to inject services, database
sessions, and configuration into route functions.

Why dependency injection?
  - Decouples route handlers from concrete implementations
  - Makes testing straightforward: override any dependency with a mock
  - Makes lifecycle management explicit (open/close database sessions per request)
  - Enables future features like rate limiting, auditing, caching as middleware

Current state (Phase 1):
  - get_db_session: Placeholder — raises NotImplementedError to signal
    that routes needing a DB session are not yet ready.
  - get_settings: Returns the validated settings singleton.

Evolution plan:
  Phase 2: Implement get_db_session with async SQLAlchemy session factory
  Phase 2: Add get_document_repository, get_knowledge_base_service
  Phase 4: Add get_current_user (JWT authentication)
  Phase 4: Add require_permission (RBAC authorization)
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from app.config.settings import Settings, get_settings

# ---------------------------------------------------------------------------
# Settings dependency
# ---------------------------------------------------------------------------


def get_app_settings() -> Settings:
    """
    Dependency that returns the validated application settings.

    Usage in route handlers:
        @router.get("/example")
        async def example(cfg: AppSettings) -> ...:
            return {"env": cfg.ENVIRONMENT}
    """
    return get_settings()


# Annotated type alias — keeps route signatures clean and readable
AppSettings = Annotated[Settings, Depends(get_app_settings)]


# ---------------------------------------------------------------------------
# Database session dependency (Phase 2 placeholder)
# ---------------------------------------------------------------------------


async def get_db_session() -> AsyncGenerator[None, None]:
    """
    Yield an async database session scoped to a single HTTP request.

    Phase 2 implementation will:
      1. Call async_session_factory() to obtain an AsyncSession
      2. Yield the session inside a try/finally block
      3. Commit on success, rollback on exception
      4. Close the session in the finally block

    Example usage (Phase 2+):
        DbSession = Annotated[AsyncSession, Depends(get_db_session)]

        @router.post("/documents")
        async def create_document(db: DbSession, ...) -> ...:
            ...
    """
    raise NotImplementedError(
        "Database session is not yet configured. "
        "This dependency will be implemented in Phase 2 when the "
        "SQLAlchemy async engine and session factory are set up. "
        "See docs/03-development-roadmap.md for the Phase 2 plan."
    )
    yield
