"""Async SQLAlchemy engine lifecycle for the Phase 2 PostgreSQL database."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config.settings import settings

engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,
)


async def initialize_database() -> None:
    """Enable pgvector and create the Phase 2 schema when configured to do so."""
    if not settings.DATABASE_AUTO_CREATE:
        return

    # Import models before create_all so every table is registered on Base.metadata.
    import app.models  # noqa: F401
    from app.models.base import Base

    async with engine.begin() as connection:
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        await connection.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Close database connections during application shutdown."""
    await engine.dispose()
