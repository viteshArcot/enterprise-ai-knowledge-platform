import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from tests.evaluation.evaluator import calculate_metrics_for_question

def test_recall_at_1():
    expected_pages = {12}
    retrieved_chunks = [
        {"rank": 1, "page_number": 12},
        {"rank": 2, "page_number": 20},
    ]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is True
    assert res["hit_at_10"] is True
    assert res["hit_at_20"] is True
    assert res["first_relevant_rank"] == 1
    assert res["rr"] == 1.0
    assert res["is_complete"] is True

def test_recall_at_k():
    expected_pages = {24}
    retrieved_chunks = [
        {"rank": i, "page_number": i} for i in range(1, 25)
    ]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is False
    assert res["hit_at_10"] is False
    assert res["hit_at_20"] is False
    assert res["first_relevant_rank"] == 24
    assert res["rr"] == 1.0 / 24.0
    assert res["is_complete"] is True

def test_no_relevant_result():
    expected_pages = {99}
    retrieved_chunks = [
        {"rank": i, "page_number": i} for i in range(1, 20)
    ]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is False
    assert res["hit_at_20"] is False
    assert res["first_relevant_rank"] == 0
    assert res["rr"] == 0.0
    assert res["is_complete"] is False

def test_partial_evidence_retrieval():
    expected_pages = {12, 24}
    retrieved_chunks = [
        {"rank": 1, "page_number": 12},
        {"rank": 2, "page_number": 25},
    ]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is True
    assert res["first_relevant_rank"] == 1
    assert res["rr"] == 1.0
    assert res["is_complete"] is False

def test_complete_evidence_retrieval():
    expected_pages = {12, 24}
    retrieved_chunks = [
        {"rank": 2, "page_number": 12},
        {"rank": 5, "page_number": 24},
    ]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is True
    assert res["first_relevant_rank"] == 2
    assert res["rr"] == 0.5
    assert res["is_complete"] is True

def test_duplicate_retrieved_chunks():
    expected_pages = {10}
    retrieved_chunks = [
        {"rank": 1, "page_number": 10},
        {"rank": 2, "page_number": 10},
    ]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is True
    assert res["first_relevant_rank"] == 1
    assert res["rr"] == 1.0
    assert res["is_complete"] is True
    assert len(res["found_expected_pages"]) == 1

def test_empty_retrieval():
    expected_pages = {1}
    retrieved_chunks = []
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is False
    assert res["rr"] == 0.0
    assert res["is_complete"] is False

def test_missing_expected_evidence():
    expected_pages = set()
    retrieved_chunks = [{"rank": 1, "page_number": 5}]
    res = calculate_metrics_for_question(expected_pages, retrieved_chunks)
    assert res["hit_at_5"] is False
    assert res["rr"] == 0.0
    assert res["is_complete"] is False

if __name__ == "__main__":
    test_recall_at_1()
    test_recall_at_k()
    test_no_relevant_result()
    test_partial_evidence_retrieval()
    test_complete_evidence_retrieval()
    test_duplicate_retrieved_chunks()
    test_empty_retrieval()
    test_missing_expected_evidence()
    print("All tests passed.")
