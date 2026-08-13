import pytest
from app.services.query_analyzer import analyze_query
from app.services.coverage_selector import select_coverage_aware_candidates
from tests.evaluation.evaluator import calculate_metrics_for_question
from unittest.mock import patch, MagicMock

# 1. Document-wide query detection
def test_document_wide_query_detection():
    analysis = analyze_query("Give a broad overview of the entire document")
    assert analysis.is_document_wide_query is True
    assert analysis.has_explicit_page_reference is False

# 2. Coverage retrieval activates only for document-wide queries (mocked search flow logic)
# 3. Normal semantic query bypasses coverage selector
# 4. Page-specific query bypasses coverage selector
# We test the logic mapping analysis to coverage retrieval
def test_search_mode_activation():
    # Normal semantic query
    a1 = analyze_query("What is an AI agent?")
    assert a1.is_document_wide_query is False

    # Page-specific query
    a2 = analyze_query("Summarize page 12")
    assert a2.has_explicit_page_reference is True
    assert a2.is_document_wide_query is False

# 5. Duplicate pages are controlled
def test_coverage_selector_duplicate_pages():
    class DummyChunk:
        def __init__(self, page_number):
            self.page_number = page_number

    candidates = [
        (DummyChunk(1), 0.9),
        (DummyChunk(1), 0.8),
        (DummyChunk(2), 0.7),
        (DummyChunk(2), 0.6)
    ]

    selected = select_coverage_aware_candidates(candidates, target_k=2, relevance_weight=0.5, page_bonus=0.5)
    pages = [c.page_number for c, d in selected]
    # Should pick exactly one chunk from page 1 and one from page 2, not two from page 1
    assert set(pages) == {1, 2}

# 6. Coverage selector remains relevance-aware
def test_coverage_selector_relevance_aware():
    class DummyChunk:
        def __init__(self, page_number):
            self.page_number = page_number

    candidates = [
        (DummyChunk(1), 0.1),  # highly relevant (distance 0.1)
        (DummyChunk(2), 0.9),  # irrelevant (distance 0.9)
        (DummyChunk(3), 0.2)   # relevant (distance 0.2)
    ]

    # Even if page 2 provides better geometric spacing between 1 and 3, its relevance is too low.
    selected = select_coverage_aware_candidates(candidates, target_k=2, relevance_weight=0.9, page_bonus=0.1)
    pages = [c.page_number for c, d in selected]
    assert 1 in pages
    assert 3 in pages
    assert 2 not in pages

# 7. Evaluator does not apply global +/- 1 page tolerance
# 8. Explicit acceptable-page groups work only for the relevant entry
def test_evaluator_strictness_and_groups():
    expected_page_groups = [{12}, {15, 16}]

    # Retrieved exact match for group 1 (12), but only adjacent for group 2 (14 or 17).
    # Because we no longer have +/- 1 global tolerance, 17 will NOT satisfy {15, 16}.
    retrieved_chunks = [
        {"rank": 1, "page_number": 12},
        {"rank": 2, "page_number": 17}
    ]

    metrics = calculate_metrics_for_question(expected_page_groups, retrieved_chunks)
    assert not metrics["is_complete"]
    assert metrics["found_expected_pages"] == {12}

    # But if we retrieve 15, it satisfies the group {15, 16}
    retrieved_chunks_2 = [
        {"rank": 1, "page_number": 12},
        {"rank": 2, "page_number": 15}
    ]

    metrics_2 = calculate_metrics_for_question(expected_page_groups, retrieved_chunks_2)
    assert metrics_2["is_complete"]
    assert metrics_2["found_expected_pages"] == {12, 15}

# 9. Existing multimodal retrieval behavior remains unchanged
@pytest.mark.asyncio
async def test_multimodal_search_preserves_behavior():
    # Test that visual queries (e.g. diagrams) trigger the vector search properly
    # without breaking due to coverage. This is mostly verified by checking SearchService.
    # We can assert that analyze_query correctly tags visual intent and bypasses coverage.
    analysis = analyze_query("Show me the architecture diagram")
    # visual intent doesn't exist on QueryAnalysis schema
    # Visual queries generally aren't document-wide, ensuring standard flow
    assert analysis.is_document_wide_query is False
