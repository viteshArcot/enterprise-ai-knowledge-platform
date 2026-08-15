"""Chat endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.dependencies import get_chat_service
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from app.services.chat import ChatService

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    document_ids: list[uuid.UUID] | None = None


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Create a new conversation."""
    return await chat_service.create_conversation(title=data.title)


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    chat_service: ChatService = Depends(get_chat_service),
) -> list[ConversationResponse]:
    """List all conversations."""
    return await chat_service.list_conversations(limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Get a specific conversation."""
    return await chat_service.get_conversation(conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def rename_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Rename a conversation."""
    return await chat_service.rename_conversation(conversation_id, data.title)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    chat_service: ChatService = Depends(get_chat_service),
) -> None:
    await chat_service.delete_conversation(conversation_id)

@router.post("/{conversation_id}/documents/{document_id}", response_model=ConversationResponse)
async def attach_document(
    conversation_id: uuid.UUID,
    document_id: uuid.UUID,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Attach a document to a conversation."""
    return await chat_service.attach_document(conversation_id, document_id)


@router.delete("/{conversation_id}/documents/{document_id}", response_model=ConversationResponse)
async def detach_document(
    conversation_id: uuid.UUID,
    document_id: uuid.UUID,
    chat_service: ChatService = Depends(get_chat_service),
) -> ConversationResponse:
    """Detach a document from a conversation."""
    return await chat_service.detach_document(conversation_id, document_id)



import json

@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Send a message to a conversation and stream the response."""

    async def sse_stream():
        try:
            yield "event: ready\ndata: {}\n\n"
            async for chunk in chat_service.stream_chat(conversation_id, request.message, document_ids=request.document_ids):
                # Use JSON encoding safely
                encoded_chunk = json.dumps(chunk)
                yield f"data: {encoded_chunk}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            import structlog
            structlog.get_logger(__name__).error("stream_chat_failed", error=str(e))
            error_data = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
