import pytest
import re
from app.services.query_analyzer import analyze_query

def test_document_wide_intent_detection():
    # Positive examples
    positive_queries = [
        "Give a broad overview of all architecture patterns discussed in the guide.",
        "Summarize the entire document.",
        "Summarize the whole document.",
        "Give me an overview of this guide.",
        "Give me an overview of the document.",
        "What are the main topics covered in this document?",
        "What topics are discussed throughout the guide?",
        "Summarize all the architecture patterns in the document.",
        "Give me a comprehensive overview of the guide.",
        "What are all the major architecture patterns discussed?",
        "Explain the document as a whole."
    ]

    for query in positive_queries:
        analysis = analyze_query(query)
        assert analysis.is_document_wide_query is True, f"Failed on: {query}"
        assert analysis.has_explicit_page_reference is False

    # Negative examples
    negative_queries = [
        "What are the main components of a single-agent architecture?",
        "What is on page 20?",
        "Explain the single-agent architecture diagram.",
        "Compare sequential and parallel workflows.",
        "What are the architecture patterns for parallel workflows?",
        "What are the most important 20 ideas?",
        "What does page 16 say?",
        "Which page talks about single-agent architecture?"
    ]

    for query in negative_queries:
        analysis = analyze_query(query)
        assert analysis.is_document_wide_query is False, f"Failed on: {query}"
        if "page" in query.lower() and re.search(r'\b(?:page|pg\.?|p\.)\s+(\d+)\b', query, flags=re.IGNORECASE):
            assert analysis.has_explicit_page_reference is True
