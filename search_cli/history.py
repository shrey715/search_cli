import json
import time
from pathlib import Path
from typing import List

HISTORY_PATH = Path.home() / ".local" / "share" / "terch" / "history.jsonl"
MAX_ENTRIES = 500


class HistoryStore:
    """Append-only JSONL log of searches and opened links."""

    def __init__(self, path: Path = HISTORY_PATH):
        self.path = path

    def _append(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        self._trim()

    def _trim(self) -> None:
        try:
            lines = self.path.read_text().splitlines()
        except OSError:
            return
        if len(lines) > MAX_ENTRIES:
            self.path.write_text("\n".join(lines[-MAX_ENTRIES:]) + "\n")

    def log_search(self, provider: str, query: str, result_count: int) -> None:
        self._append(
            {
                "type": "search",
                "timestamp": time.time(),
                "provider": provider,
                "query": query,
                "result_count": result_count,
            }
        )

    def log_open(self, url: str, title: str) -> None:
        self._append({"type": "open", "timestamp": time.time(), "url": url, "title": title})

    def recent_searches(self, limit: int = 50) -> List[dict]:
        """Most-recent-first, deduplicated by (provider, query)."""
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text().splitlines()
        except OSError:
            return []

        seen = set()
        results = []
        for line in reversed(lines):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "search":
                continue
            key = (entry.get("provider"), entry.get("query"))
            if key in seen:
                continue
            seen.add(key)
            results.append(entry)
            if len(results) >= limit:
                break
        return results
