"""Embedding provider contract."""

from abc import ABC, abstractmethod
from typing import Any


class EmbeddingGateway(ABC):
    """Convert batches of text into equal-dimension embedding vectors."""

    model_name: str
    dimensions: int

    @abstractmethod
    async def embed(self, inputs: list[str | list[dict[str, Any]]]) -> list[list[float]]:
        """Embed text or multimodal content into vectors."""
