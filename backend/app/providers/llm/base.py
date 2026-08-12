"""LLM provider contract."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageAttachment:
    """An image attached to a prompt message."""
    data: bytes
    mime_type: str


@dataclass(frozen=True)
class PromptMessage:
    """A provider-neutral chat prompt message."""

    role: str
    content: str
    images: list[ImageAttachment] | None = None


class LLMGateway(ABC):
    """Generate complete or streamed chat responses from a prompt."""

    model_name: str

    @abstractmethod
    async def complete(self, messages: list[PromptMessage]) -> str:
        """Return a complete response."""

    @abstractmethod
    async def stream(self, messages: list[PromptMessage]) -> AsyncIterator[str]:
        """Yield response text fragments in order."""
