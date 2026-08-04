"""Metadata extraction for parsed source documents."""

from pathlib import Path
from typing import Any

from app.ingestion.parsers.base import ParsedDocument


def extract_metadata(file_name: str, parsed: ParsedDocument) -> dict[str, Any]:
    """Return stable metadata that does not require an additional document pass."""
    title = Path(file_name).stem.replace("_", " ").replace("-", " ").strip()
    return {
        "title": title or file_name,
        "page_count": parsed.page_count,
        "word_count": len(parsed.text.split()),
        "character_count": len(parsed.text),
        **parsed.metadata,
    }
