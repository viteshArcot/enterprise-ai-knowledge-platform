"""Base classes for reranker providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.models.chunk import Chunk


@dataclass(frozen=True)
class RerankResult:
    """A single reranked chunk with its associated scores."""
    chunk: Chunk
    vector_similarity: float
    rerank_score: float
    original_rank: int


class RerankerGateway(ABC):
    """Abstract interface for external reranking APIs."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        candidates: list[tuple[Chunk, float]],
        top_k: int
    ) -> list[RerankResult]:
        """
        Rerank a set of candidate chunks against a query.

        Args:
            query: The user's search query.
            candidates: List of tuples containing the candidate Chunk and its vector distance.
            top_k: The number of results to return after reranking.

        Returns:
            A list of RerankResult, ordered by descending rerank_score.
            If the reranker fails, this should fall back to returning the original
            candidates in their original order.
        """
        pass
