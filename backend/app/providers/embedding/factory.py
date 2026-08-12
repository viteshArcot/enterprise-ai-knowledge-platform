"""Factory for the Phase 2 embedding provider."""

from app.config.settings import Settings
from app.providers.embedding.base import EmbeddingGateway
from app.providers.embedding.openrouter import OpenRouterEmbeddingGateway


def create_embedding_gateway(config: Settings) -> EmbeddingGateway:
    """Construct the configured OpenRouter embedding gateway."""
    return OpenRouterEmbeddingGateway(config)
