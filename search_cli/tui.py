import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from search_cli.cache import ResultCache
from search_cli.engine import perform_search
from search_cli.exporters import export_results
from search_cli.fuzzy import fuzzy_score
from search_cli.history import HistoryStore
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider

MAX_SUGGESTIONS = 6


class ResultItem(ListItem):
    """A single row in the results list."""

    def __init__(self, result: SearchResult, marked: bool = False):
        self.result = result
        self.marked = marked
        super().__init__(Label(self._label()))

    def _label(self) -> Text:
        text = Text()
        text.append("✓ " if self.marked else "  ", style="bold green")
        text.append(f"{self.result.index:>3} ", style="bold magenta")
        text.append(self.result.title, style="bold cyan")
        if self.result.display_domain:
            text.append(f"  ({self.result.display_domain})", style="dim green")
        return text

    def set_marked(self, marked: bool) -> None:
        self.marked = marked
        self.query_one(Label).update(self._label())


class SearchInput(Input):
    """The new-search Input; Tab accepts the highlighted history suggestion.

    (Bound here rather than at the App level because Screen reserves plain
    "tab" for focus-cycling, which would otherwise shadow an App binding.)
    """

    BINDINGS = [Binding("tab", "accept_suggestion", "Accept suggestion", show=False)]

    def action_accept_suggestion(self) -> None:
        self.app.action_accept_suggestion()


class HistoryScreen(ModalScreen[Optional[dict]]):
    """Modal listing recent searches; selecting one re-runs it."""

    CSS = """
    HistoryScreen {
        align: center middle;
    }
    #history-box {
        width: 80%;
        height: 80%;
        border: solid $accent;
        background: $surface;
    }
    #history-title {
        padding: 1 2 0 2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape,q", "dismiss_screen", "Close", show=False),
    ]

    def __init__(self, entries: List[dict]):
        super().__init__()
        self.entries = entries

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="history-box"):
            yield Static("Recent searches (Enter to re-run, Esc to close)", id="history-title")
            yield ListView(id="history-list")

    def on_mount(self) -> None:
        list_view = self.query_one("#history-list", ListView)
        for entry in self.entries:
            label = f"{entry['query']}  ·  {entry['provider']}  ·  {entry.get('result_count', '?')} result(s)"
            item = ListItem(Label(label))
            item.entry = entry
            list_view.append(item)
        if not self.entries:
            list_view.append(ListItem(Label("No search history yet.")))
        list_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        entry = getattr(event.item, "entry", None)
        self.dismiss(entry)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)


class SearchApp(App):
    """Full-screen keyboard-driven search browser."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #body {
        height: 1fr;
    }
    #results {
        width: 45%;
        border-right: solid $panel;
    }
    #results ListItem {
        height: 1;
    }
    #results ListItem Label {
        width: 1fr;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }
    #preview {
        width: 1fr;
        padding: 1 2;
    }
    #status {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }
    #search-box {
        display: none;
        dock: bottom;
        height: auto;
    }
    #search-box.visible {
        display: block;
    }
    #search-suggestions {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }
    #filter-input, #export-input {
        display: none;
        dock: bottom;
    }
    #filter-input.visible, #export-input.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("j,down", "cursor_down", "Down", show=False),
        Binding("k,up", "cursor_up", "Up", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),
        Binding("enter,o", "open_selected", "Open"),
        Binding("space", "toggle_mark", "Mark"),
        Binding("O", "open_marked", "Open marked"),
        Binding("y", "copy_link", "Copy URL"),
        Binding("r", "refresh_search", "Refresh"),
        Binding("slash", "new_search", "New search"),
        Binding("f", "filter", "Filter"),
        Binding("n", "next_page", "Next page"),
        Binding("N", "prev_page", "Prev page"),
        Binding("p", "switch_provider", "Switch engine"),
        Binding("e", "export", "Export"),
        Binding("H", "show_history", "History"),
        Binding("escape", "cancel_input", "Cancel", show=False),
        Binding("q,ctrl+c", "quit", "Quit"),
    ]

    def __init__(
        self,
        query: str,
        results: List[SearchResult],
        provider: BaseSearchProvider,
        providers: Dict[str, BaseSearchProvider],
        max_results: int = 10,
        cache: Optional[ResultCache] = None,
        history: Optional[HistoryStore] = None,
    ):
        super().__init__()
        self.query_str = query
        self.results = results
        self.provider = provider
        self.providers = providers
        self.max_results = max_results
        self.cache = cache
        self.history = history
        self.marked_links: Set[str] = set()
        self.offset = 0
        self._suggestions: List[str] = []
        self._suggestion_index = -1
        self.title = "terch"

    @property
    def page(self) -> int:
        return self.offset // self.max_results + 1 if self.max_results else 1

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            yield ListView(id="results")
            with VerticalScroll(id="preview"):
                yield Static(id="preview-content")
        yield Static(id="status")
        with Vertical(id="search-box"):
            yield Static(id="search-suggestions")
            yield SearchInput(
                placeholder="New search query... (↑/↓ history, Tab to accept)", id="search-input"
            )
        yield Input(placeholder="Filter results...", id="filter-input")
        yield Input(placeholder="Export to path (.md or .json)...", id="export-input")
        yield Footer()

    def on_mount(self) -> None:
        self._populate(self.results)

    # -- rendering -----------------------------------------------------

    def _populate(self, results: List[SearchResult]) -> None:
        """A fresh page of results has arrived: replace the source of truth."""
        self.results = results
        self.marked_links.clear()
        self.sub_title = f"{self.query_str} · {self.provider.display_name} · page {self.page}"
        self._render_list(results)

    def _status_text(self) -> str:
        if not self.results:
            return "No results found."
        return (
            f"Page {self.page} · {len(self.results)} result(s) "
            f"from [bold]{self.provider.display_name}[/bold]"
        )

    def _render_list(self, results: List[SearchResult], focus_list: bool = True) -> None:
        """Render `results` into the list without touching self.results."""
        list_view = self.query_one("#results", ListView)
        list_view.clear()
        for res in results:
            list_view.append(ResultItem(res, marked=res.link in self.marked_links))
        if not self.query_one("#filter-input", Input).has_class("visible"):
            self._set_status(self._status_text())
        if results:
            list_view.index = 0
        self._update_preview()
        if focus_list:
            list_view.focus()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _current_item(self) -> Optional[ResultItem]:
        list_view = self.query_one("#results", ListView)
        if list_view.index is None:
            return None
        child = list_view.highlighted_child
        return child if isinstance(child, ResultItem) else None

    def _update_preview(self) -> None:
        preview = self.query_one("#preview-content", Static)
        item = self._current_item()
        if item is None:
            preview.update("[dim]No result selected.[/dim]")
            return
        res = item.result
        body = Text()
        body.append(f"[{res.index}] ", style="bold magenta")
        body.append(f"{res.title}\n\n", style="bold cyan")
        body.append(f"{res.link}\n\n", style="underline blue")
        body.append(res.snippet or "(no description)", style="white")
        preview.update(body)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._update_preview()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # ListView consumes the "enter" key itself, so opening happens here.
        self.action_open_selected()

    # -- navigation -----------------------------------------------------

    def action_cursor_down(self) -> None:
        if self._search_input_visible():
            self._cycle_suggestion(1)
            return
        self.query_one("#results", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._search_input_visible():
            self._cycle_suggestion(-1)
            return
        self.query_one("#results", ListView).action_cursor_up()

    def action_cursor_top(self) -> None:
        list_view = self.query_one("#results", ListView)
        if list_view.children:
            list_view.index = 0

    def action_cursor_bottom(self) -> None:
        list_view = self.query_one("#results", ListView)
        if list_view.children:
            list_view.index = len(list_view.children) - 1

    # -- opening / marking ------------------------------------------------

    def action_open_selected(self) -> None:
        item = self._current_item()
        if item is None:
            return
        self._open_link(item.result)

    def _open_link(self, result: SearchResult) -> None:
        webbrowser.open(result.link)
        if self.history is not None:
            self.history.log_open(result.link, result.title)

    def action_toggle_mark(self) -> None:
        item = self._current_item()
        if item is None:
            return
        if item.result.link in self.marked_links:
            self.marked_links.discard(item.result.link)
            item.set_marked(False)
        else:
            self.marked_links.add(item.result.link)
            item.set_marked(True)
        self.action_cursor_down()

    def action_open_marked(self) -> None:
        targets = [res for res in self.results if res.link in self.marked_links]
        if not targets:
            item = self._current_item()
            targets = [item.result] if item else []
        if not targets:
            self._set_status("Nothing marked to open.")
            return
        for res in targets:
            self._open_link(res)
        self._set_status(f"Opened {len(targets)} link(s).")

    def action_copy_link(self) -> None:
        item = self._current_item()
        if item is None:
            return
        self.copy_to_clipboard(item.result.link)
        self._set_status(f"Copied to clipboard: {item.result.link}")

    # -- filter (local, no network) ----------------------------------------

    def action_filter(self) -> None:
        self._show_input("filter-input")

    def _apply_filter(self, query: str) -> None:
        if not query:
            self._render_list(self.results, focus_list=False)
            self._set_status(self._status_text())
            return
        scored = []
        for res in self.results:
            haystack = f"{res.title} {res.display_domain or ''} {res.snippet}"
            score = fuzzy_score(query, haystack)
            if score is not None:
                scored.append((score, res))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        filtered = [res for _, res in scored]
        self._render_list(filtered, focus_list=False)
        self._set_status(f"Filter '{query}': {len(filtered)}/{len(self.results)} match(es)")

    # -- pagination ----------------------------------------------------

    def action_next_page(self) -> None:
        self.offset += self.max_results
        self._run_search(self.query_str, offset=self.offset, log_history=False)

    def action_prev_page(self) -> None:
        if self.offset == 0:
            self._set_status("Already on the first page.")
            return
        self.offset = max(0, self.offset - self.max_results)
        self._run_search(self.query_str, offset=self.offset, log_history=False)

    # -- history-aware search suggestions --------------------------------

    def _search_input_visible(self) -> bool:
        return self.query_one("#search-box").has_class("visible")

    def _recent_queries(self) -> List[str]:
        if self.history is None:
            return []
        seen = set()
        queries = []
        for entry in self.history.recent_searches(limit=200):
            q = entry["query"]
            if q in seen:
                continue
            seen.add(q)
            queries.append(q)
        return queries

    def _update_search_suggestions(self, typed: str) -> None:
        queries = self._recent_queries()
        if typed:
            scored = [(fuzzy_score(typed, q), q) for q in queries]
            scored = [(score, q) for score, q in scored if score is not None]
            scored.sort(key=lambda pair: pair[0], reverse=True)
            self._suggestions = [q for _, q in scored[:MAX_SUGGESTIONS]]
        else:
            self._suggestions = queries[:MAX_SUGGESTIONS]
        self._suggestion_index = -1
        self._render_suggestions()

    def _cycle_suggestion(self, direction: int) -> None:
        if not self._suggestions:
            return
        n = len(self._suggestions)
        if self._suggestion_index == -1:
            self._suggestion_index = 0 if direction > 0 else n - 1
        else:
            self._suggestion_index = (self._suggestion_index + direction) % n
        self._render_suggestions()

    def _render_suggestions(self) -> None:
        box = self.query_one("#search-suggestions", Static)
        if not self._suggestions:
            box.update("")
            return
        text = Text("history: ", style="dim")
        for i, q in enumerate(self._suggestions):
            if i > 0:
                text.append("  ·  ", style="dim")
            text.append(q, style="reverse bold" if i == self._suggestion_index else "dim")
        box.update(text)

    def action_accept_suggestion(self) -> None:
        if not self._suggestions:
            return
        idx = self._suggestion_index if self._suggestion_index != -1 else 0
        chosen = self._suggestions[idx]
        search_input = self.query_one("#search-input", Input)
        search_input.value = chosen
        search_input.cursor_position = len(chosen)

    # -- search / provider --------------------------------------------------

    def action_refresh_search(self) -> None:
        self._run_search(self.query_str, offset=self.offset)

    def action_new_search(self) -> None:
        self._show_input("search-input")

    def action_export(self) -> None:
        self._show_input("export-input")

    def action_show_history(self) -> None:
        if self.history is None:
            self._set_status("History is disabled.")
            return
        self.push_screen(HistoryScreen(self.history.recent_searches()), self._on_history_selected)

    def _on_history_selected(self, entry: Optional[dict]) -> None:
        if entry is None:
            return
        provider = self.providers.get(entry["provider"])
        if provider is not None:
            self.provider = provider
        self.query_str = entry["query"]
        self.offset = 0
        self._run_search(self.query_str)

    def _hide_all_inputs(self) -> None:
        self.query_one("#search-box").remove_class("visible")
        self.query_one("#filter-input", Input).remove_class("visible")
        self.query_one("#export-input", Input).remove_class("visible")

    def _show_input(self, input_id: str) -> None:
        self._hide_all_inputs()
        if input_id == "search-input":
            box = self.query_one("#search-box")
            box.add_class("visible")
            search_input = self.query_one("#search-input", Input)
            search_input.value = ""
            search_input.focus()
            self._update_search_suggestions("")
        else:
            widget = self.query_one(f"#{input_id}", Input)
            widget.value = ""
            widget.add_class("visible")
            widget.focus()

    def action_cancel_input(self) -> None:
        was_filtering = self.query_one("#filter-input", Input).has_class("visible")
        self._hide_all_inputs()
        self.query_one("#results", ListView).focus()
        if was_filtering:
            self._render_list(self.results)
            self._set_status(self._status_text())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._apply_filter(event.value)
        elif event.input.id == "search-input":
            self._update_search_suggestions(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        value = event.value.strip()

        if input_id == "search-input" and self._suggestion_index != -1 and self._suggestions:
            value = self._suggestions[self._suggestion_index]

        self._hide_all_inputs()
        self.query_one("#results", ListView).focus()

        if input_id == "search-input":
            if value:
                self.query_str = value
                self.offset = 0
                self._run_search(value)
        elif input_id == "filter-input":
            pass  # already applied live; Enter just returns focus to the list
        elif input_id == "export-input":
            self._do_export(value)

    def _do_export(self, path_str: str) -> None:
        if not path_str:
            return
        targets = [res for res in self.results if res.link in self.marked_links] or self.results
        if not targets:
            self._set_status("Nothing to export.")
            return
        try:
            export_results(targets, Path(path_str))
        except OSError as exc:
            self._set_status(f"[bold red]Export failed:[/bold red] {exc}")
            return
        self._set_status(f"Exported {len(targets)} result(s) to {path_str}")

    def action_switch_provider(self) -> None:
        names = list(self.providers.keys())
        if len(names) < 2:
            self._set_status("Only one search engine configured.")
            return
        current = names.index(self.provider.name)
        self.provider = self.providers[names[(current + 1) % len(names)]]
        self.offset = 0
        self._run_search(self.query_str)

    @work(exclusive=True, thread=True)
    def _run_search(self, query: str, offset: int = 0, log_history: bool = True) -> None:
        self.call_from_thread(self._set_status, f"Searching {self.provider.display_name}...")
        try:
            results = perform_search(
                self.provider,
                query,
                self.max_results,
                offset=offset,
                cache=self.cache,
                history=self.history if log_history else None,
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[bold red]Search error:[/bold red] {exc}")
            return
        self.call_from_thread(self._populate, results)
