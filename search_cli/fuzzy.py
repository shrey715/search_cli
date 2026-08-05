from typing import Optional


def fuzzy_score(query: str, text: str) -> Optional[float]:
    """
    Subsequence fuzzy matcher, fzf-style: every character of `query` must
    appear in `text` in order (case-insensitive). Returns a score where
    higher is a better match, or None if `query` isn't a subsequence.
    """
    if not query:
        return 0.0

    haystack = text.lower()
    needle = query.lower()

    search_from = 0
    first_match: Optional[int] = None
    consecutive = 0
    score = 0.0

    for ch in needle:
        idx = haystack.find(ch, search_from)
        if idx == -1:
            return None
        if first_match is None:
            first_match = idx
        if idx == search_from:
            consecutive += 1
            score += 2 * consecutive
        else:
            consecutive = 0
            score += 1
        search_from = idx + 1

    span = search_from - first_match
    score -= span * 0.1
    return score
