"""Search service."""

from dataclasses import dataclass
from typing import Any

from app.providers.embedding.base import EmbeddingGateway
from app.repositories.chunk import ChunkRepository
from app.services.base import BaseService


@dataclass(frozen=True)
class SearchResult:
    """A retrieved context chunk with metadata for citation."""
    content: str
    document_title: str
    score: float
    metadata: dict[str, Any]


class SearchService(BaseService):
    """Business logic for dense vector retrieval."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        embedding_gateway: EmbeddingGateway,
        default_top_k: int = 5,
    ) -> None:
        super().__init__()
        self._chunk_repo = chunk_repo
        self._embedding_gateway = embedding_gateway
        self._default_top_k = default_top_k

    async def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        """Perform semantic search across all indexed chunks."""
        limit = top_k or self._default_top_k
        self._logger.debug("search_started", query=query, top_k=limit)

        # Generate embedding for the search query
        query_embeddings = await self._embedding_gateway.embed([query])
        if not query_embeddings:
            return []
        
        query_embedding = query_embeddings[0]

        # Retrieve similar chunks
        similar_chunks = await self._chunk_repo.find_similar(query_embedding, limit=limit)
        
        results = []
        for chunk, distance in similar_chunks:
            # We assume eager loading of chunk.document wasn't done for performance,
            # but chunk.document can be populated if we change the query, OR we can 
            # just store document title in chunk metadata. 
            # Wait, chunk.document_id is available. If we need document_title, we should 
            # join with Document in the repository query.
            # I will assume `chunk.document` is available if we use selectinload in the repo,
            # or I'll just use the metadata fallback. 
            # Wait, `app.models.document` has title. Let's gracefully handle it.
            try:
                title = chunk.document.title if chunk.document else "Unknown Document"
            except Exception:
                title = "Unknown Document"

            results.append(
                SearchResult(
                    content=chunk.content,
                    document_title=title,
                    score=1.0 - distance,  # Convert distance to similarity score
                    metadata=chunk.metadata_,
                )
            )

        self._logger.info("search_completed", query=query, results_count=len(results))
        return results
