"""Chunk schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChunkBase(BaseModel):
    document_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: int
    char_count: int
    page_number: int | None = None
    metadata_: dict[str, Any] = {}
    embedding: list[float] | None = None


class ChunkCreate(ChunkBase):
    pass


class ChunkUpdate(BaseModel):
    embedding: list[float] | None = None


class ChunkResponse(ChunkBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
