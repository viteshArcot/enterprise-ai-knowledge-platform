"""Document persistence model."""

import enum
from typing import Any

from sqlalchemy import BigInteger, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DocumentStatus(str, enum.Enum):
    """Lifecycle states for an uploaded document."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(UUIDMixin, TimestampMixin, Base):
    """An uploaded source file and its ingestion state."""

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        default=DocumentStatus.UPLOADING,
        nullable=False,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
