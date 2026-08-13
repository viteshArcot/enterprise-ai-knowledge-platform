"""Conversation and Message schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.message import MessageRole
from app.schemas.document import DocumentResponse


class MessageBase(BaseModel):
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[dict[str, Any]] = []
    token_count: int | None = None
    model_name: str | None = None
    latency_ms: int | None = None


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    pass


class MessageResponse(MessageBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationBase(BaseModel):
    title: str | None = None


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    title: str | None = None


class ConversationResponse(ConversationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []
    documents: list["DocumentResponse"] = []

    model_config = ConfigDict(from_attributes=True)
