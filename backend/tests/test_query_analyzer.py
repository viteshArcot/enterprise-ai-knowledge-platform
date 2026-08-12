from app.services.query_analyzer import analyze_query

def test_analyze_query_positive_cases():
    test_cases = [
        ("What is on page 20?", 20),
        ("Summarize page 16.", 16),
        ("What does Page 12 say?", 12),
        ("Explain p. 8.", 8),
        ("According to pg. 24...", 24),
        ("From pg 13", 13),
        ("page 1", 1),
        ("page 999", 999),
        ("Page 20?", 20),
        ("page 20,", 20),
        ("page 20.", 20),
        ("page    20", 20),
        ("PAGE 20", 20)
    ]
    
    for query, expected_page in test_cases:
        analysis = analyze_query(query)
        assert analysis.has_explicit_page_reference is True
        assert analysis.page_number == expected_page

def test_analyze_query_negative_cases():
    test_cases = [
        "What are the 20 most important ideas?",
        "What happened in 2024?",
        "What are the 3 components?",
        "How does the 20-step workflow work?",
        "Compare 2 approaches.",
        "page -20",
        "page20",
        "Explain page. No, wait."
    ]
    
    for query in test_cases:
        analysis = analyze_query(query)
        assert analysis.has_explicit_page_reference is False
        assert analysis.page_number is None

if __name__ == "__main__":
    test_analyze_query_positive_cases()
    test_analyze_query_negative_cases()
    print("All query analyzer tests passed.")
