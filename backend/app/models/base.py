"""
SQLAlchemy declarative base and shared model mixins.

All ORM models in this application MUST inherit from Base.
Common columns (id, created_at, updated_at) are provided via mixins
so they are defined once and applied consistently.

Design decisions:
  - UUIDs as primary keys: No collision risk across distributed systems,
    no information leakage (sequential IDs reveal business metrics), and
    safe to generate client-side if needed.
  - All timestamps in UTC: Consistent regardless of server location.
    Never store local time in a database.
  - server_default for timestamps: Let the database set the value to avoid
    clock skew between application servers.

Evolution plan:
  Phase 2: Add Document, KnowledgeBase, Chunk models
  Phase 3: Add Embedding model (pgvector column)
  Phase 4: Add User, ApiKey models
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.

    Usage:
        class MyModel(Base):
            __tablename__ = "my_table"
            ...

    All models sharing this Base are tracked in Base.metadata,
    which Alembic uses to generate migrations.
    """

    # Override in subclasses to provide PostgreSQL-specific type mappings
    type_annotation_map: dict[type, Any] = {
        datetime: DateTime(timezone=True),
    }


class UUIDMixin:
    """
    Mixin that adds a UUID primary key column.

    Using uuid.uuid4() as server_default ensures the database always
    generates a valid UUID even if the application forgets to provide one.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Universally unique identifier for this record.",
    )


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at audit columns.

    These are server-side defaults — the database sets them, not the application.
    This avoids clock skew issues across multiple application instances.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created (UTC).",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        doc="Timestamp when the record was last updated (UTC).",
    )
