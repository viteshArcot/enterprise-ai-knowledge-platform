from typing import Any

def select_coverage_aware_candidates(
    candidates: list[tuple[Any, float]],
    target_k: int,
    relevance_weight: float = 0.8,
    page_bonus: float = 0.1
) -> list[tuple[Any, float]]:
    """
    Greedy selection algorithm to balance relevance and page coverage.

    Args:
        candidates: List of (Chunk, distance) tuples, ordered by distance asc.
        target_k: The number of candidates to select.
        relevance_weight: Weight given to vector similarity (0.0 to 1.0).
        page_bonus: Additive bonus for choosing a chunk from a previously unseen page.

    Returns:
        List of selected (Chunk, distance) tuples.
    """
    if not candidates:
        return []

    # Calculate max possible page distance in the candidate pool
    pages = [c.page_number for c, _ in candidates if c.page_number is not None]
    if pages:
        max_page_dist = float(max(pages) - min(pages))
        if max_page_dist == 0:
            max_page_dist = 1.0
    else:
        max_page_dist = 1.0

    selected = []
    selected_pages = []

    # Create a mutable copy of remaining candidates
    remaining = list(candidates)

    while remaining and len(selected) < target_k:
        best_idx = -1
        best_score = -float('inf')

        for i, (chunk, distance) in enumerate(remaining):
            # Normalize distance to similarity (higher is better)
            sim = 1.0 - (distance if distance is not None else 1.0)

            score = relevance_weight * sim

            page = chunk.page_number
            if page is not None:
                if not selected_pages:
                    # First page gets max bonus
                    score += page_bonus
                else:
                    # Calculate distance to closest already selected page
                    min_dist = min(abs(page - sp) for sp in selected_pages)

                    if min_dist == 0:
                        # Same page - strictly deduplicate
                        score -= 100.0
                    else:
                        # Bonus scales with distance to ensure we spread out
                        norm_dist = min_dist / max_page_dist
                        score += page_bonus * norm_dist
            else:
                if not selected_pages:
                    score += page_bonus

            if score > best_score:
                best_score = score
                best_idx = i

        # Greedily pick the best candidate
        if best_idx != -1:
            chosen_chunk, chosen_dist = remaining.pop(best_idx)
            selected.append((chosen_chunk, chosen_dist))
            if chosen_chunk.page_number is not None:
                selected_pages.append(chosen_chunk.page_number)
        else:
            break

    return selected
