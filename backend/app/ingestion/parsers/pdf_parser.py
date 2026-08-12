"""PDF text extraction backed by PyMuPDF."""

import fitz

from app.core.exceptions import IngestionError
from app.ingestion.parsers.base import DocumentParser, ParsedDocument


class PdfParser(DocumentParser):
    """Extract text and page count from digital PDFs."""

    extensions = ("pdf",)

    def parse(self, content: bytes, file_name: str) -> ParsedDocument:
        """Extract text and visual representations from each page without writing an intermediate file."""
        import base64
        try:
            from app.ingestion.parsers.base import ParsedPage
            document = fitz.open(stream=content, filetype="pdf")
            try:
                pages = []
                for i, page in enumerate(document):
                    text = page.get_text("text")
                    image_base64 = None
                    
                    # Heuristic: visual if has images or drawings
                    images = page.get_images()
                    drawings = page.get_drawings()
                    
                    if images or drawings:
                        # Render page at 72 DPI (matrix 1.0) to bound memory
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                        img_data = pix.tobytes("png")
                        image_base64 = base64.b64encode(img_data).decode("utf-8")
                        
                    pages.append(ParsedPage(page_number=i+1, text=text, image_base64=image_base64))
                    
                full_text = "\n\n".join(p.text for p in pages)
                return ParsedDocument(text=full_text, pages=pages, page_count=document.page_count)
            finally:
                document.close()
        except (fitz.FileDataError, RuntimeError, ValueError) as exc:
            raise IngestionError(f"Unable to extract text from '{file_name}'.") from exc
