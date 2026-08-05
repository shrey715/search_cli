import webbrowser
from typing import Dict, List, Optional

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from search_cli.models import SearchResult
from search_cli.providers.base import BaseSearchProvider


class ResultItem(ListItem):
    """A single row in the results list. Tracks its own multi-select state."""

    def __init__(self, result: SearchResult):
        self.result = result
        self.marked = False
        super().__init__(Label(self._label()))

    def _label(self) -> Text:
        text = Text()
        text.append("✓ " if self.marked else "  ", style="bold green")
        text.append(f"{self.result.index:>3} ", style="bold magenta")
        text.append(self.result.title, style="bold cyan")
        if self.result.display_domain:
            text.append(f"  ({self.result.display_domain})", style="dim green")
        return text

    def toggle_mark(self) -> None:
        self.marked = not self.marked
        self.query_one(Label).update(self._label())


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
    #search-input {
        display: none;
        dock: bottom;
    }
    #search-input.visible {
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
        Binding("p", "switch_provider", "Switch engine"),
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
    ):
        super().__init__()
        self.query_str = query
        self.results = results
        self.provider = provider
        self.providers = providers
        self.max_results = max_results
        self.title = "terch"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            yield ListView(id="results")
            with VerticalScroll(id="preview"):
                yield Static(id="preview-content")
        yield Static(id="status")
        yield Input(placeholder="New search query...", id="search-input")
        yield Footer()

    def on_mount(self) -> None:
        self._populate(self.results)

    def _populate(self, results: List[SearchResult]) -> None:
        self.results = results
        list_view = self.query_one("#results", ListView)
        list_view.clear()
        for res in results:
            list_view.append(ResultItem(res))
        self.sub_title = f"{self.query_str} · {self.provider.display_name}"
        self._set_status(
            f"{len(results)} result(s) from [bold]{self.provider.display_name}[/bold]"
            if results
            else "No results found."
        )
        if results:
            list_view.index = 0
        self._update_preview()
        list_view.focus()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _current_item(self) -> Optional[ResultItem]:
        list_view = self.query_one("#results", ListView)
        if list_view.index is None or not self.results:
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
        if self.results:
            list_view.index = 0

    def action_cursor_bottom(self) -> None:
        list_view = self.query_one("#results", ListView)
        if self.results:
            list_view.index = len(self.results) - 1

    # -- opening / marking ------------------------------------------------

    def action_open_selected(self) -> None:
        item = self._current_item()
        if item is None:
            return
        webbrowser.open(item.result.link)
        self._set_status(f"Opened: {item.result.link}")

    def action_toggle_mark(self) -> None:
        item = self._current_item()
        if item is None:
            return
        item.toggle_mark()
        self.action_cursor_down()

    def action_open_marked(self) -> None:
        list_view = self.query_one("#results", ListView)
        marked = [
            child for child in list_view.children if isinstance(child, ResultItem) and child.marked
        ]
        targets = marked or ([self._current_item()] if self._current_item() else [])
        if not targets:
            self._set_status("Nothing marked to open.")
            return
        for item in targets:
            webbrowser.open(item.result.link)
        self._set_status(f"Opened {len(targets)} link(s).")

    def action_copy_link(self) -> None:
        item = self._current_item()
        if item is None:
            return
        self.copy_to_clipboard(item.result.link)
        self._set_status(f"Copied to clipboard: {item.result.link}")

    # -- search / provider --------------------------------------------------

    def action_refresh_search(self) -> None:
        self._run_search(self.query_str)

    def action_new_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        search_input.add_class("visible")
        search_input.focus()

    def action_cancel_input(self) -> None:
        search_input = self.query_one("#search-input", Input)
        if search_input.has_class("visible"):
            search_input.remove_class("visible")
            self.query_one("#results", ListView).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        event.input.remove_class("visible")
        self.query_one("#results", ListView).focus()
        if query:
            self.query_str = query
            self._run_search(query)

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
            results = self.provider.search(query, max_results=self.max_results)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[bold red]Search error:[/bold red] {exc}")
            return
        self.call_from_thread(self._populate, results)
