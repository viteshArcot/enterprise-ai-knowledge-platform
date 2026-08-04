"""PDF text extraction backed by PyMuPDF."""

import fitz

from app.core.exceptions import IngestionError
from app.ingestion.parsers.base import DocumentParser, ParsedDocument


class PdfParser(DocumentParser):
    """Extract text and page count from digital PDFs."""

    extensions = ("pdf",)

    def parse(self, content: bytes, file_name: str) -> ParsedDocument:
        """Extract text from each page without writing an intermediate file."""
        try:
            document = fitz.open(stream=content, filetype="pdf")
            try:
                pages = [page.get_text("text") for page in document]
                return ParsedDocument(text="\n\n".join(pages), page_count=document.page_count)
            finally:
                document.close()
        except (fitz.FileDataError, RuntimeError, ValueError) as exc:
            raise IngestionError(f"Unable to extract text from '{file_name}'.") from exc
