"""Message repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.sqlalchemy import BaseSqlAlchemyRepository
from app.schemas.conversation import MessageCreate, MessageUpdate


class MessageRepository(BaseSqlAlchemyRepository[Message, MessageCreate, MessageUpdate]):
    """Repository for managing Messages."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Message, session)
