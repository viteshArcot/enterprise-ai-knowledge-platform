"""Reranker gateway factory."""

from app.config.settings import Settings
from app.providers.reranker.base import RerankerGateway
from app.providers.reranker.openrouter import OpenRouterRerankerGateway


def create_reranker_gateway(config: Settings) -> RerankerGateway:
    """Factory for creating the appropriate reranker gateway."""
    # Only OpenRouter is supported right now for reranking, but if we had local models
    # or other providers, we would conditionally select them here.
    return OpenRouterRerankerGateway(config)
