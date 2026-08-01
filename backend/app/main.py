"""
FastAPI application factory.

Why an application factory?
  Creating the FastAPI instance inside a function (rather than at module level)
  makes testing clean: each test suite can call create_application() to get
  a fresh, fully configured app with its own middleware and routes — no shared
  global state to worry about.

Composition root responsibilities:
  1. Create the FastAPI instance with metadata
  2. Register middleware (CORS, request ID, etc.)
  3. Register global exception handlers
  4. Mount all API routers
  5. Configure lifespan events (startup / shutdown)

Architecture rule:
  NO business logic belongs in this file.
  If you find yourself adding logic here, it belongs in a service or middleware.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


# =============================================================================
# Lifespan — startup and shutdown event handler
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown using the modern lifespan protocol.

    FastAPI's lifespan replaces the deprecated @app.on_event("startup") pattern.
    Resources initialized here are available for the entire application lifetime.

    Startup sequence (current Phase 1):
      1. Configure structured logging

    Planned startup additions:
      Phase 2: Initialize async SQLAlchemy engine and connection pool
      Phase 2: Run Alembic migrations in development mode
      Phase 3: Initialize vector store client (pgvector / Pinecone)
      Phase 3: Warm up embedding model cache

    Shutdown sequence:
      Phase 2: Close database connection pool
      Phase 3: Close vector store connection
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging()

    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        version=settings.API_VERSION,
        debug=settings.DEBUG,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("application_shutdown")


# =============================================================================
# Application factory
# =============================================================================


def create_application() -> FastAPI:
    """
    Create and return a fully configured FastAPI application instance.

    This is the single entry point for application assembly. Import and call
    this function in tests to get an isolated application instance.
    """
    # Disable interactive docs in production to reduce attack surface
    _docs_url = "/api/docs" if settings.ENVIRONMENT != "production" else None
    _redoc_url = "/api/redoc" if settings.ENVIRONMENT != "production" else None
    _openapi_url = "/api/openapi.json" if settings.ENVIRONMENT != "production" else None

    application = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url=_docs_url,
        redoc_url=_redoc_url,
        openapi_url=_openapi_url,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    # CORS: Allow the frontend to make cross-origin requests to the API.
    # Phase 4: Replace with more restrictive settings in production.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Phase 2: Add request ID middleware (X-Request-ID header → structlog context)
    # Phase 4: Add authentication middleware

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(application)

    # ── Routes ────────────────────────────────────────────────────────────────
    application.include_router(api_v1_router, prefix="/api/v1")

    return application


# Module-level app instance used by uvicorn: `uvicorn app.main:app`
app: FastAPI = create_application()
