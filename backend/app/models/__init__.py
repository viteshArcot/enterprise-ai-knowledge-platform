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
