import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from search_cli.models import SearchResult

CACHE_PATH = Path.home() / ".cache" / "terch" / "cache.json"


class ResultCache:
    """A flat JSON-backed cache of search results, keyed by provider/query/max_results/offset."""

    def __init__(self, path: Path = CACHE_PATH, ttl: int = 900):
        self.path = path
        self.ttl = ttl

    @staticmethod
    def _key(provider: str, query: str, max_results: int, offset: int) -> str:
        return f"{provider}:{max_results}:{offset}:{query.strip().lower()}"

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def get(
        self, provider: str, query: str, max_results: int, offset: int = 0
    ) -> Optional[List[SearchResult]]:
        entries = self._load()
        entry = entries.get(self._key(provider, query, max_results, offset))
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > self.ttl:
            return None
        return [SearchResult(**item) for item in entry["results"]]

    def set(
        self, provider: str, query: str, max_results: int, results: List[SearchResult], offset: int = 0
    ) -> None:
        entries = self._load()
        entries[self._key(provider, query, max_results, offset)] = {
            "timestamp": time.time(),
            "results": [asdict(r) for r in results],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries))
