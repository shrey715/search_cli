import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from search_cli.models import SearchResult


def export_results(results: List[SearchResult], path: Path) -> None:
    """Write results to `path` as JSON (.json) or Markdown (any other suffix)."""
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps([asdict(r) for r in results], indent=2))
        return

    lines = []
    for res in results:
        lines.append(f"- [{res.title}]({res.link})")
        if res.snippet:
            lines.append(f"  {res.snippet}")
    path.write_text("\n".join(lines) + "\n")
