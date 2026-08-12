"""Deterministic paragraph, sentence, and word-aware token chunking."""

import re
from dataclasses import dataclass

import tiktoken

from app.core.exceptions import ValidationAppError

_SENTENCES = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class TextChunk:
    """A chunk ready for persistence and embedding."""

    content: str
    chunk_index: int
    token_count: int
    char_count: int
    page_number: int | None = None


class RecursiveTokenChunker:
    """Split text on natural boundaries before falling back to words."""

    def __init__(self, chunk_size: int, overlap: int, encoding_name: str) -> None:
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._encoding = tiktoken.get_encoding(encoding_name)

    def chunk(self, text: str, start_index: int = 0, page_number: int | None = None) -> list[TextChunk]:
        """Create deterministic token-bounded chunks from non-empty text."""
        if not text.strip():
            raise ValidationAppError("Cannot chunk an empty document.")
        units = self._split_units(text)
        chunks: list[TextChunk] = []
        current = ""
        for unit in units:
            candidate = f"{current} {unit}".strip()
            if current and self._token_count(candidate) > self._chunk_size:
                chunks.append(self._make_chunk(current, start_index + len(chunks), page_number))
                current = self._overlap_text(current)
                candidate = f"{current} {unit}".strip()
            while self._token_count(candidate) > self._chunk_size:
                token_ids = self._encoding.encode(candidate)
                head = self._encoding.decode(token_ids[: self._chunk_size])
                chunks.append(self._make_chunk(head.strip(), start_index + len(chunks), page_number))
                current = self._encoding.decode(token_ids[self._chunk_size - self._overlap :]).strip()
                candidate = current
            current = candidate
        if current:
            chunks.append(self._make_chunk(current, start_index + len(chunks), page_number))
        return chunks

    def _split_units(self, text: str) -> list[str]:
        units: list[str] = []
        for paragraph in (part.strip() for part in text.split("\n\n") if part.strip()):
            sentences = _SENTENCES.split(paragraph)
            for sentence in sentences:
                if self._token_count(sentence) <= self._chunk_size:
                    units.append(sentence)
                else:
                    units.extend(word for word in sentence.split() if word)
        return units

    def _overlap_text(self, text: str) -> str:
        if not self._overlap:
            return ""
        return self._encoding.decode(self._encoding.encode(text)[-self._overlap :]).strip()

    def _token_count(self, text: str) -> int:
        return len(self._encoding.encode(text))

    def _make_chunk(self, content: str, index: int, page_number: int | None = None) -> TextChunk:
        return TextChunk(
            content=content,
            chunk_index=index,
            token_count=self._token_count(content),
            char_count=len(content),
            page_number=page_number,
        )
