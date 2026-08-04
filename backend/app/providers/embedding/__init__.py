"""Embedding provider abstractions and Gemini implementation."""

from app.providers.embedding.factory import create_embedding_gateway

__all__ = ["create_embedding_gateway"]
