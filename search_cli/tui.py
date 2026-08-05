import webbrowser
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from search_cli.cache import ResultCache
from search_cli.engine import perform_search
from search_cli.exporters import export_results
from search_cli.fuzzy import fuzzy_score
from search_cli.history import HistoryStore
from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider

INPUT_IDS = ("search-input", "filter-input", "export-input")


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
    #search-input, #filter-input, #export-input {
        display: none;
        dock: bottom;
    }
    #search-input.visible, #filter-input.visible, #export-input.visible {
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
        self.title = "terch"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            yield ListView(id="results")
            with VerticalScroll(id="preview"):
                yield Static(id="preview-content")
        yield Static(id="status")
        yield Input(placeholder="New search query...", id="search-input")
        yield Input(placeholder="Filter results...", id="filter-input")
        yield Input(placeholder="Export to path (.md or .json)...", id="export-input")
        yield Footer()

    def on_mount(self) -> None:
        self._populate(self.results)

    # -- rendering -----------------------------------------------------

    def _populate(self, results: List[SearchResult]) -> None:
        """A fresh set of results has arrived: replace the source of truth."""
        self.results = results
        self.marked_links.clear()
        self.sub_title = f"{self.query_str} · {self.provider.display_name}"
        self._render_list(results)

    def _render_list(self, results: List[SearchResult], focus_list: bool = True) -> None:
        """Render `results` into the list without touching self.results."""
        list_view = self.query_one("#results", ListView)
        list_view.clear()
        for res in results:
            list_view.append(ResultItem(res, marked=res.link in self.marked_links))
        if not self.query_one("#filter-input", Input).has_class("visible"):
            self._set_status(
                f"{len(results)} result(s) from [bold]{self.provider.display_name}[/bold]"
                if results
                else "No results found."
            )
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
        self.query_one("#results", ListView).action_cursor_down()

    def action_cursor_up(self) -> None:
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
            self._set_status(f"{len(self.results)} result(s) from [bold]{self.provider.display_name}[/bold]")
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

    # -- search / provider --------------------------------------------------

    def action_refresh_search(self) -> None:
        self._run_search(self.query_str)

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
        self._run_search(self.query_str)

    def _show_input(self, input_id: str) -> None:
        for other_id in INPUT_IDS:
            widget = self.query_one(f"#{other_id}", Input)
            if other_id == input_id:
                widget.value = ""
                widget.add_class("visible")
                widget.focus()
            else:
                widget.remove_class("visible")

    def action_cancel_input(self) -> None:
        filter_input = self.query_one("#filter-input", Input)
        was_filtering = filter_input.has_class("visible")
        for input_id in INPUT_IDS:
            self.query_one(f"#{input_id}", Input).remove_class("visible")
        self.query_one("#results", ListView).focus()
        if was_filtering:
            self._render_list(self.results)
            self._set_status(f"{len(self.results)} result(s) from [bold]{self.provider.display_name}[/bold]")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._apply_filter(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        value = event.value.strip()
        event.input.remove_class("visible")
        self.query_one("#results", ListView).focus()

        if input_id == "search-input":
            if value:
                self.query_str = value
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
        self._run_search(self.query_str)

    @work(exclusive=True, thread=True)
    def _run_search(self, query: str) -> None:
        self.call_from_thread(self._set_status, f"Searching {self.provider.display_name}...")
        try:
            results = perform_search(
                self.provider, query, self.max_results, cache=self.cache, history=self.history
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[bold red]Search error:[/bold red] {exc}")
            return
        self.call_from_thread(self._populate, results)
