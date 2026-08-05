from typing import List, Optional

from search_cli.cache import ResultCache
from search_cli.history import HistoryStore
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider


def perform_search(
    provider: BaseSearchProvider,
    query: str,
    max_results: int,
    cache: Optional[ResultCache] = None,
    history: Optional[HistoryStore] = None,
) -> List[SearchResult]:
    """Search, transparently serving/populating the cache and logging history."""
    results = None
    if cache is not None:
        results = cache.get(provider.name, query, max_results)

    if results is None:
        results = provider.search(query, max_results=max_results)
        if cache is not None:
            cache.set(provider.name, query, max_results, results)

    if history is not None:
        history.log_search(provider.name, query, len(results))

    return results
