import os
import requests
from typing import List
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider, strip_html


class BraveProvider(BaseSearchProvider):
    def __init__(self):
        self.api_key = os.getenv("BRAVE_API_KEY", "")

    @property
    def name(self) -> str:
        return "brave"

    @property
    def display_name(self) -> str:
        return "Brave Search"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "count": min(max_results, 20)}

        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()

        if "error" in data:
            message = data["error"]
            if isinstance(message, dict):
                message = message.get("message", "Unknown error")
            raise RuntimeError(f"Brave API Error: {message}")

        results: List[SearchResult] = []
        for idx, item in enumerate(data.get("web", {}).get("results", []), start=1):
            results.append(
                SearchResult(
                    title=item.get("title", "No Title"),
                    link=item.get("url", ""),
                    snippet=strip_html(item.get("description", "")),
                    index=idx,
                )
            )

        return results
