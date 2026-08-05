import os
import requests
from typing import List
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider, strip_html


class SearXNGProvider(BaseSearchProvider):
    """Queries a self-hosted or public SearXNG instance's JSON API.

    Requires SEARXNG_URL (e.g. https://searx.example.com) with JSON output
    enabled on the instance -- most public instances disable it by default.
    """

    def __init__(self):
        self.base_url = os.getenv("SEARXNG_URL", "").rstrip("/")

    @property
    def name(self) -> str:
        return "searxng"

    @property
    def display_name(self) -> str:
        return "SearXNG"

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        url = f"{self.base_url}/search"
        params = {"q": query, "format": "json"}

        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            raise RuntimeError(f"SearXNG returned HTTP {res.status_code}")
        data = res.json()

        results: List[SearchResult] = []
        for idx, item in enumerate(data.get("results", [])[:max_results], start=1):
            results.append(
                SearchResult(
                    title=item.get("title", "No Title"),
                    link=item.get("url", ""),
                    snippet=strip_html(item.get("content", "")),
                    index=idx,
                )
            )

        return results
