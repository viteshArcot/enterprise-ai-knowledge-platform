"""Document schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentBase(BaseModel):
    title: str
    file_name: str
    file_type: str
    file_size_bytes: int
    file_path: str
    status: DocumentStatus = DocumentStatus.UPLOADING
    source_url: str | None = None
    metadata_: dict[str, Any] = {}
    chunk_count: int | None = None
    error_message: str | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: str | None = None
    status: DocumentStatus | None = None
    metadata_: dict[str, Any] | None = None
    chunk_count: int | None = None
    error_message: str | None = None


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
