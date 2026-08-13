import re
from dataclasses import dataclass

@dataclass(frozen=True)
class QueryAnalysis:
    """Result of analyzing a search query for structural intent."""
    original_query: str
    page_number: int | None
    has_explicit_page_reference: bool
    is_document_wide_query: bool

def analyze_query(query: str) -> QueryAnalysis:
    """
    Analyzes a natural language query for explicit page references.

    This uses a deterministic regular expression to extract page numbers.
    It intentionally requires explicit markers (like 'page', 'pg.', 'p.')
    and whitespace to avoid false positives on arbitrary numbers.
    """
    # Regex breakdown:
    # \b          : Word boundary (ensures we don't match 'spage')
    # (?:...)     : Non-capturing group for the prefix
    # page|pg\.?|p\. : Matches 'page', 'pg', 'pg.', or 'p.'
    # \s+         : One or more whitespace characters
    # (\d+)       : Captures one or more digits (the page number)
    # \b          : Word boundary (ensures we don't capture partial numbers or floating points like 20.5 incorrectly)

    pattern = r'\b(?:page|pg\.?|p\.)\s+(\d+)\b'
    match = re.search(pattern, query, flags=re.IGNORECASE)

    if match:
        page_number = int(match.group(1))
        return QueryAnalysis(
            original_query=query,
            page_number=page_number,
            has_explicit_page_reference=True,
            is_document_wide_query=False
        )

    # Document-wide query intent detection
    # This must not trigger on specific questions, so we look for holistic framing.
    doc_wide_pattern = r'\b(?:broad overview|summarize.*(?:entire|whole|all)|main topics|overview of this|overview of the document|comprehensive overview|all the.*discussed|document as a whole|throughout the)\b'
    is_doc_wide = bool(re.search(doc_wide_pattern, query, flags=re.IGNORECASE))

    return QueryAnalysis(
        original_query=query,
        page_number=None,
        has_explicit_page_reference=False,
        is_document_wide_query=is_doc_wide
    )
