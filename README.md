# terch

[![PyPI version](https://badge.fury.io/py/terch.svg)](https://badge.fury.io/py/terch)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> A modular, lightning-fast CLI search engine built with Rich UI formatting and interactive keyboard navigation.

---

## Features

- **Modular Architecture:** Easily plug in custom search engines — ships with Google Custom Search, DuckDuckGo, Bing, Brave, and SearXNG.
- **Full-Screen TUI:** Built with [Textual](https://textual.textualize.io/) — a compact, scrollable list of results next to a live detail preview, so you never have to scroll up and down to read a snippet.
- **Stays Open:** Pressing `Enter` opens a link in your default browser without closing the app, so you can open several results from one search.
- **Multi-Select:** Mark multiple results and open them all at once.
- **Fuzzy Filter:** Narrow down the currently loaded results locally (no extra network round-trip) as you type.
- **In-App Search & Provider Switching:** Run a new query or switch search engines without leaving the app.
- **Result Caching:** Repeat queries are served from a local cache instead of re-hitting the API.
- **Search History:** Every search (and every link you open) is logged; browse and re-run past searches from inside the app.
- **Export:** Dump the current (or marked) results to Markdown or JSON.
- **Config File:** Set defaults (provider, result count, cache behavior) once in `~/.config/terch/config.toml`.
- **Automatic Fallbacks:** Defaults to DuckDuckGo (zero setup required) if no other provider is configured.
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
| `f`              | Fuzzy-filter the loaded results locally    |
| `p`              | Cycle to the next configured search engine |
| `r`              | Re-run the current search                  |
| `e`              | Export results (marked, or all) to a file  |
| `H`              | Browse & re-run recent searches            |
| `Esc`            | Cancel the current input box / filter      |
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

# Bypass the result cache for this run
terch "breaking news" --no-cache

# Search and export straight to a file, skipping the TUI entirely
terch "python rich cli" --export results.md

```

This drops you into a full-screen TUI — see [Keybindings](#keybindings) above for how to navigate it.

---

## Configuration & API Keys

`terch` works out-of-the-box using DuckDuckGo without requiring any API keys. Other providers need credentials, set via a `.env` file, `.env.local` (local overrides, gitignored), or exported to your shell:

```bash
# Google Custom Search: https://developers.google.com/custom-search/v1/introduction
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_CX_ID="your_custom_search_engine_id"

# Bing Web Search (Azure Cognitive Services)
export BING_API_KEY="your_bing_api_key"

# Brave Search API: https://brave.com/search/api/
export BRAVE_API_KEY="your_brave_api_key"

# A SearXNG instance with JSON output enabled
export SEARXNG_URL="https://your-searxng-instance.example.com"

```

Copy [`.env.example`](.env.example) as a starting point. `.env` and `.env.local` are both gitignored, so your keys never get committed.

### Config File

Set defaults once in `~/.config/terch/config.toml` instead of passing flags every time:

```toml
default_provider = "duckduckgo"
max_results = 15
cache_enabled = true
cache_ttl = 900          # seconds
history_enabled = true

```

CLI flags (`-p`, `-n`, `--no-cache`) always override the config file.

You don't need to open the file by hand — `terch config` manages it from the terminal:

```bash
terch config show                        # print the full current config
terch config get max_results             # print one value
terch config set max_results 15          # set a value (creates the file if needed)
terch config set default_provider none   # clear an optional value
terch config unset max_results           # reset one key back to its default
terch config path                        # print the config file's location

```

### Caching & History

Searches are cached on disk (`~/.cache/terch/cache.json`) for `cache_ttl` seconds (default 15 minutes), so re-running the same query against the same provider doesn't hit the network again. Disable it per-run with `--no-cache`, or permanently via `cache_enabled = false` in the config file.

Every search and every link you open is logged to `~/.local/share/terch/history.jsonl`. Press `H` in the TUI to browse recent searches and re-run one with `Enter`.

### Exporting Results

Press `e` in the TUI and type a path — marked results are exported if any are marked, otherwise all currently loaded results are. The format is chosen by extension: `.json` for structured data, anything else (e.g. `.md`) for a Markdown list of links. `--export PATH` does the same thing from the command line for one-shot scripting, skipping the TUI entirely.

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
