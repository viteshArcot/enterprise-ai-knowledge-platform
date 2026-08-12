"""Contracts shared by document parsers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedPage:
    """A single page of extracted content."""
    page_number: int
    text: str
    image_base64: str | None = None

@dataclass(frozen=True)
class ParsedDocument:
    """Text and lightweight source metadata extracted from an uploaded file."""
    text: str
    pages: list[ParsedPage] = field(default_factory=list)
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentParser(ABC):
    """Convert raw bytes for a supported file type into extracted text."""

    extensions: tuple[str, ...]

    @abstractmethod
    def parse(self, content: bytes, file_name: str) -> ParsedDocument:
        """Parse document bytes or raise an IngestionError."""
