"""UTF-8 text and Markdown parser."""

from app.core.exceptions import IngestionError
from app.ingestion.parsers.base import DocumentParser, ParsedDocument


class TextParser(DocumentParser):
    """Decode plain-text sources without introducing a Markdown rendering dependency."""

    extensions = ("txt", "md", "markdown")

    def parse(self, content: bytes, file_name: str) -> ParsedDocument:
        """Decode UTF-8 text while returning a clear error for malformed input."""
        from app.ingestion.parsers.base import ParsedPage
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise IngestionError(f"'{file_name}' is not valid UTF-8 text.") from exc
        return ParsedDocument(text=text, pages=[ParsedPage(page_number=1, text=text)])
