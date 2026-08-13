"""Conversation persistence model."""

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

conversation_documents = Table(
    "conversation_documents",
    Base.metadata,
    Column("conversation_id", ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
)


class Conversation(UUIDMixin, TimestampMixin, Base):
    """An ordered set of user and assistant messages."""

    __tablename__ = "conversations"

    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", passive_deletes=True, lazy="selectin"
    )
    documents: Mapped[list["Document"]] = relationship(
        secondary=conversation_documents,
        lazy="selectin"
    )
