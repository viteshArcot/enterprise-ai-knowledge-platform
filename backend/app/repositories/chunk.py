"""Chunk repository."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models.chunk import Chunk
from app.repositories.sqlalchemy import BaseSqlAlchemyRepository
from app.schemas.chunk import ChunkCreate, ChunkUpdate


class ChunkRepository(BaseSqlAlchemyRepository[Chunk, ChunkCreate, ChunkUpdate]):
    """Repository for managing Chunk entities and vector search."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Chunk, session)

    async def create_many(self, chunks: list[ChunkCreate]) -> None:
        """Batch insert chunks for performance."""
        # Using add_all for batch insert (can be optimized further with insert().values() if needed)
        entities = [
            self._model(**(c.model_dump(exclude_unset=True) if hasattr(c, "model_dump") else c))
            for c in chunks
        ]
        self._session.add_all(entities)
        await self._session.flush()

    async def find_similar(
        self, query_embedding: list[float], limit: int = 5, page_number: int | None = None, document_ids: list[__import__('uuid').UUID] | None = None
    ) -> list[tuple[Chunk, float]]:
        """
        Perform vector similarity search using pgvector.
        Returns tuples of (Chunk, distance), ordered by lowest distance (highest similarity).
        Cosine distance is used: 1 - (embedding <=> query_embedding).
        """
        # vector <=> operator is cosine distance
        stmt = (
            select(Chunk, Chunk.embedding.cosine_distance(query_embedding).label("distance"))
            .where(Chunk.embedding.is_not(None))
        )

        if page_number is not None:
            stmt = stmt.where(Chunk.page_number == page_number)

        if document_ids is not None and len(document_ids) > 0:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))

        stmt = (
            stmt.options(joinedload(Chunk.document))
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row.Chunk, row.distance) for row in result]

    async def delete_by_document_id(self, document_id: str | int | __import__('uuid').UUID) -> None:
        """Delete all chunks for a specific document."""
        from sqlalchemy import delete
        stmt = delete(Chunk).where(Chunk.document_id == document_id)
        await self._session.execute(stmt)
        await self._session.flush()
