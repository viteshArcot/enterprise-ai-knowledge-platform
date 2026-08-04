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
    """Delete a conversation."""
    await chat_service.delete_conversation(conversation_id)


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Send a message to a conversation and stream the response."""
    
    # We yield SSE formatted chunks
    async def sse_stream():
        async for chunk in chat_service.stream_chat(conversation_id, request.message):
            # Replace newlines in chunks with a specific format or just yield data line
            # For simplicity with basic fetch we can just send the text directly.
            # But true SSE requires `data: {chunk}\n\n`
            # For a pure text stream we can just yield the string. The frontend can read the text stream.
            # Let's yield pure text chunks, making it a simple readable stream on the frontend.
            yield chunk

    return StreamingResponse(sse_stream(), media_type="text/plain")
