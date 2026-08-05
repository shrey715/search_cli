# terch

[![PyPI version](https://badge.fury.io/py/terch.svg)](https://badge.fury.io/py/terch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> A modular, lightning-fast CLI search engine built with Rich UI formatting and interactive keyboard navigation.

---

## Features

- **Modular Architecture:** Easily plug in custom search engines (Google Custom Search API, DuckDuckGo, Tavily, etc.).
- **Full-Screen TUI:** Built with [Textual](https://textual.textualize.io/) — a compact, scrollable list of results next to a live detail preview, so you never have to scroll up and down to read a snippet.
- **Stays Open:** Pressing `Enter` opens a link in your default browser without closing the app, so you can open several results from one search.
- **Multi-Select:** Mark multiple results and open them all at once.
- **In-App Search & Provider Switching:** Run a new query or switch search engines without leaving the app.
- **Automatic Fallbacks:** Defaults to DuckDuckGo (zero setup required) if Google API keys are not provided.
- **Built with Modern Python Tooling:** Managed via `uv` and packaged using `hatchling`.

### Keybindings

| Key(s)           | Action                                     |
| ---------------- | ------------------------------------------ |
| `↑`/`↓`, `k`/`j` | Move selection                             |
| `g` / `G`        | Jump to first / last result                |
| `Enter` / `o`    | Open selected link in browser (stays open) |
| `Space`          | Mark / unmark the selected result          |
| `O`              | Open all marked links (or selection)       |
| `y`              | Copy the selected link to the clipboard    |
| `/`              | Run a new search                           |
| `p`              | Cycle to the next configured search engine |
| `r`              | Re-run the current search                  |
| `Esc`            | Cancel the search input box                |
| `q` / `Ctrl+C`   | Quit                                       |

---

## Quickstart

### Global Installation via `uv` (Recommended)

```bash
uv tool install terch

```

### Global Installation via `pipx`

```bash
pipx install terch

```

---

## Usage

Run `terch` (or `search`) directly from your command line:

```bash
# Quick search (uses DuckDuckGo by default if no keys configured)
terch "IIIT Hyderabad"

# Specify provider explicitly
terch "python rich cli" -p duckduckgo

# Limit result count
terch "latest machine learning papers" -n 3

```

This drops you into a full-screen TUI — see [Keybindings](#keybindings) above for how to navigate it.

---

## Configuration & API Keys

`terch` works out-of-the-box using DuckDuckGo without requiring any API keys.

To use **Google Custom Search API**, set your credentials in a `.env` file or export them to your shell environment:

```bash
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_CX_ID="your_custom_search_engine_id"

```

Or copy [`.env.example`](.env.example) to `.env` (or `.env.local`) in your working directory and fill in the values:

```env
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX_ID=your_custom_search_engine_id

```

`.env` and `.env.local` are both gitignored, so your keys never get committed.

---

## Adding Custom Search Providers

`terch` uses an extensible plugin architecture. To add a new search provider:

1. Create a new class subclassing `BaseSearchProvider` in `search_cli/providers/`:

```python
from search_cli.providers.base import BaseSearchProvider
from search_cli.models import SearchResult
from typing import List

class MyProvider(BaseSearchProvider):
    @property
    def name(self) -> str:
        return "my_provider"

    @property
    def display_name(self) -> str:
        return "My Search Engine"

    def is_configured(self) -> bool:
        return True

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        # Implement API or search fetch here
        return []

```

2. Add your provider to the `REGISTRY` in `search_cli/providers/__init__.py`.

---

## Local Development

### Clone & Install Dependencies

```bash
git clone [https://github.com/shrey715/search_cli.git](https://github.com/shrey715/search_cli.git)
cd search_cli

# Install dependencies and setup virtual environment
uv sync

```

### Run Locally

```bash
uv run terch "python terminal tools"

```

---

## License

Distributed under the MIT License
