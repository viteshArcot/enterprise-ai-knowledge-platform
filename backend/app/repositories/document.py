"""Document repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.sqlalchemy import BaseSqlAlchemyRepository
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentRepository(BaseSqlAlchemyRepository[Document, DocumentCreate, DocumentUpdate]):
    """Repository for managing Document entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Document, session)

    async def get_by_file_hash(self, file_hash: str) -> Document | None:
        """Find a document by its file hash."""
        stmt = select(Document).where(
            Document.file_hash == file_hash
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
