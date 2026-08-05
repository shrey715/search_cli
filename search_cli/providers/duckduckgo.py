import requests
from bs4 import BeautifulSoup
from typing import List
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider


class DuckDuckGoProvider(BaseSearchProvider):
    @property
    def name(self) -> str:
        return "duckduckgo"

    @property
    def display_name(self) -> str:
        return "DuckDuckGo"

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5, offset: int = 0) -> List[SearchResult]:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        data = {"q": query, "s": offset}

        response = requests.post(url, data=data, headers=headers, timeout=10)
        if response.status_code != 200:
            raise RuntimeError(f"DuckDuckGo returned HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        results: List[SearchResult] = []

        for local_idx, result in enumerate(soup.find_all("div", class_="result"), start=1):
            if local_idx > max_results:
                break

            title_elem = result.find("a", class_="result__a")
            snippet_elem = result.find("a", class_="result__snippet")

            if not title_elem:
                continue

            # separator=" " fixes concatenated words like "aroundHyderabad" -> "around Hyderabad"
            title = title_elem.get_text(separator=" ", strip=True)
            link = title_elem.get("href", "")
            snippet = snippet_elem.get_text(separator=" ", strip=True) if snippet_elem else ""

            results.append(
                SearchResult(
                    title=title,
                    link=link,
                    snippet=snippet,
                    index=offset + local_idx,
                )
            )

        return results