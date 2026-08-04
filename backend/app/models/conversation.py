"""Conversation persistence model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Conversation(UUIDMixin, TimestampMixin, Base):
    """An ordered set of user and assistant messages."""

    __tablename__ = "conversations"

    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True, lazy="selectin"
    )
