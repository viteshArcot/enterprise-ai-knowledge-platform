"""Conversation repository."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.repositories.sqlalchemy import BaseSqlAlchemyRepository
from app.schemas.conversation import ConversationCreate, ConversationUpdate


class ConversationRepository(BaseSqlAlchemyRepository[Conversation, ConversationCreate, ConversationUpdate]):
    """Repository for managing Conversations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Conversation, session)

    async def get_with_messages(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Retrieve a conversation along with its messages, ordered by creation time."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await self._session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation:
            # Sort messages by created_at ascending
            conversation.messages.sort(key=lambda m: m.created_at)
        return conversation

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        """List conversations, newest first."""
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
