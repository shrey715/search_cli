import os
import requests
from typing import List
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider


class GoogleProvider(BaseSearchProvider):
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY", "")
        self.cx = os.getenv("GOOGLE_CX_ID", "")

    @property
    def name(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google Search"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.cx)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": min(max_results, 10),
        }

        res = requests.get(url, params=params, timeout=10)
        data = res.json()

        if "error" in data:
            raise RuntimeError(
                f"Google API Error: {data['error'].get('message', 'Unknown error')}"
            )

        results: List[SearchResult] = []
        for idx, item in enumerate(data.get("items", []), start=1):
            results.append(
                SearchResult(
                    title=item.get("title", "No Title"),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    index=idx,
                )
            )

        return results
