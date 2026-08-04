"""
Models package.

Exposes the SQLAlchemy Base and common mixins used across all ORM models.
Import Base from here when defining new models to ensure they are all
registered in the same metadata instance (required for Alembic migrations).

Usage:
    from app.models import Base, UUIDMixin, TimestampMixin

    class MyModel(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "my_table"
        ...
"""

from app.models.base import Base, TimestampMixin, UUIDMixin

__all__ = ["Base", "TimestampMixin", "UUIDMixin"]
"""SQLAlchemy models registered with the Phase 2 metadata."""

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.chunk import Chunk
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.message import Message, MessageRole

__all__ = [
    "Base",
    "Chunk",
    "Conversation",
    "Document",
    "DocumentStatus",
    "Message",
    "MessageRole",
    "TimestampMixin",
    "UUIDMixin",
]
