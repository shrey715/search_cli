import os
import requests
from typing import List
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider


class BingProvider(BaseSearchProvider):
    def __init__(self):
        self.api_key = os.getenv("BING_API_KEY", "")

    @property
    def name(self) -> str:
        return "bing"

    @property
    def display_name(self) -> str:
        return "Bing Search"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5, offset: int = 0) -> List[SearchResult]:
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {"q": query, "count": min(max_results, 50), "offset": offset}

        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()

        if "error" in data:
            raise RuntimeError(f"Bing API Error: {data['error'].get('message', 'Unknown error')}")

        results: List[SearchResult] = []
        for idx, item in enumerate(data.get("webPages", {}).get("value", []), start=offset + 1):
            results.append(
                SearchResult(
                    title=item.get("name", "No Title"),
                    link=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    index=idx,
                )
            )

        return results
