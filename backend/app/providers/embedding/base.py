"""Embedding provider contract."""

from abc import ABC, abstractmethod


class EmbeddingGateway(ABC):
    """Convert batches of text into equal-dimension embedding vectors."""

    model_name: str
    dimensions: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a non-empty batch of text in source order."""
