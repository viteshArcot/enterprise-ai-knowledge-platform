"""Search service."""

import uuid
from dataclasses import dataclass
from typing import Any

from app.config.settings import Settings
from app.providers.embedding.base import EmbeddingGateway
from app.providers.reranker.base import RerankerGateway
from app.repositories.chunk import ChunkRepository
from app.services.base import BaseService
from app.services.query_analyzer import analyze_query


@dataclass(frozen=True)
class SearchResult:
    """A retrieved context chunk with metadata for citation."""
    content: str
    document_title: str
    score: float
    metadata: dict[str, Any]
    file_path: str | None = None
    page_number: int | None = None
    storage_path: str | None = None


class SearchService(BaseService):
    """Business logic for dense vector retrieval."""

    def __init__(
        self,
        chunk_repo: ChunkRepository,
        embedding_gateway: EmbeddingGateway,
        reranker_gateway: RerankerGateway,
        settings: Settings,
    ) -> None:
        super().__init__()
        self._chunk_repo = chunk_repo
        self._embedding_gateway = embedding_gateway
        self._reranker_gateway = reranker_gateway
        self._settings = settings
        self._default_top_k = settings.SEARCH_DEFAULT_TOP_K

    async def search(self, query: str, top_k: int | None = None, document_ids: list[uuid.UUID] | None = None) -> list[SearchResult]:
        """Perform semantic search across all indexed chunks."""
        limit = top_k or self._default_top_k
        self._logger.debug("search_started", query=query, top_k=limit)

        # 1. Analyze the query for explicit constraints (e.g. page numbers)
        analysis = analyze_query(query)
        if analysis.has_explicit_page_reference:
            self._logger.info("search_explicit_page_detected", page=analysis.page_number)

        # 2. Generate embedding for the search query
        query_embeddings = await self._embedding_gateway.embed([query])
        if not query_embeddings:
            return []

        query_embedding = query_embeddings[0]

        from app.config.settings import settings
        if len(query_embedding) != settings.OPENROUTER_EMBEDDING_DIMENSIONS:
            self._logger.error(
                "search_invalid_embedding_dimension",
                expected=settings.OPENROUTER_EMBEDDING_DIMENSIONS,
                actual=len(query_embedding)
            )
            return []

        # Retrieve candidates, applying page constraints if any were detected
        is_coverage_retrieval = (
            analysis.is_document_wide_query
            and self._settings.RAG_COVERAGE_ENABLED
            and not analysis.has_explicit_page_reference
        )

        if is_coverage_retrieval:
            candidate_limit = self._settings.RAG_COVERAGE_CANDIDATE_LIMIT
        else:
            candidate_limit = self._settings.RERANK_CANDIDATE_LIMIT if self._settings.RERANKER_ENABLED else limit

        similar_chunks_raw = await self._chunk_repo.find_similar(
            query_embedding,
            limit=candidate_limit,
            page_number=analysis.page_number,
            document_ids=document_ids
        )

        similar_chunks = []
        for chunk, distance in similar_chunks_raw:
            if distance is None:
                self._logger.warning("search_encountered_null_distance", chunk_id=str(chunk.id))
                continue
            similar_chunks.append((chunk, distance))

        if not similar_chunks:
            return []

        # Optional Coverage Selection
        if is_coverage_retrieval:
            self._logger.info("search_coverage_retrieval_triggered", candidate_count=len(similar_chunks))
            try:
                from app.services.coverage_selector import select_coverage_aware_candidates
                similar_chunks = select_coverage_aware_candidates(
                    similar_chunks,
                    target_k=limit,
                    relevance_weight=self._settings.RAG_COVERAGE_RELEVANCE_WEIGHT,
                    page_bonus=self._settings.RAG_COVERAGE_PAGE_BONUS
                )
            except Exception as e:
                self._logger.warning("search_coverage_retrieval_failed", error=str(e))
                similar_chunks = similar_chunks[:limit]

            # Skip reranking for coverage retrieval to preserve diversity
            from app.providers.reranker.base import RerankResult
            reranked_results = [
                RerankResult(
                    chunk=c,
                    vector_similarity=1.0 - d,
                    rerank_score=0.0,
                    original_rank=i
                ) for i, (c, d) in enumerate(similar_chunks)
            ]
        # Rerank candidates if enabled
        elif self._settings.RERANKER_ENABLED:
            self._logger.debug("search_reranking_candidates", count=len(similar_chunks))
            reranked_results = await self._reranker_gateway.rerank(
                query=query,
                candidates=similar_chunks,
                top_k=limit
            )
        else:
            # Construct a dummy rerank result if disabled
            from app.providers.reranker.base import RerankResult
            reranked_results = [
                RerankResult(
                    chunk=c,
                    vector_similarity=1.0 - d,
                    rerank_score=0.0,
                    original_rank=i
                ) for i, (c, d) in enumerate(similar_chunks[:limit])
            ]

        results = []
        for result in reranked_results:
            chunk = result.chunk
            if chunk is None:
                continue

            try:
                title = chunk.document.title if chunk.document else "Unknown Document"
            except Exception:
                title = "Unknown Document"

            # Copy metadata and add rerank metadata
            metadata = dict(chunk.metadata_)
            metadata["vector_similarity"] = result.vector_similarity
            if self._settings.RERANKER_ENABLED:
                metadata["rerank_score"] = result.rerank_score
                metadata["original_rank"] = result.original_rank

            results.append(
                SearchResult(
                    content=chunk.content,
                    document_title=title,
                    score=result.vector_similarity,  # Maintain vector similarity for score property backward compatibility
                    metadata=metadata,
                    file_path=chunk.document.file_path if chunk.document else None,
                    page_number=chunk.page_number,
                    storage_path=chunk.document.storage_path if chunk.document else None,
                )
            )

        self._logger.info("search_completed", query=query, results_count=len(results))
        return results
