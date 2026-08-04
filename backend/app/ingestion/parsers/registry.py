"""Extension-to-parser registry for supported Phase 2 file formats."""

from pathlib import Path

from app.core.exceptions import UnsupportedFileTypeError
from app.ingestion.parsers.base import DocumentParser
from app.ingestion.parsers.docx_parser import DocxParser
from app.ingestion.parsers.pdf_parser import PdfParser
from app.ingestion.parsers.text_parser import TextParser


class ParserRegistry:
    """Select a parser by normalized filename extension."""

    def __init__(self, parsers: tuple[DocumentParser, ...] | None = None) -> None:
        registered = parsers or (PdfParser(), DocxParser(), TextParser())
        self._parsers = {
            extension: parser for parser in registered for extension in parser.extensions
        }

    def get_parser(self, file_name: str) -> DocumentParser:
        """Return the matching parser or reject unsupported file types."""
        extension = Path(file_name).suffix.lower().lstrip(".")
        parser = self._parsers.get(extension)
        if parser is None:
            raise UnsupportedFileTypeError(file_name)
        return parser
