import webbrowser
from typing import List
from InquirerPy.base.control import Choice
from InquirerPy import inquirer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.text import Text
from search_cli.models import SearchResult

console = Console()


def display_header(query: str, provider_name: str):
    console.print()
    header_text = f"[bold blue]Search CLI[/bold blue] [dim]|[/dim] Engine: [bold cyan]{provider_name}[/bold cyan]"
    console.rule(header_text, style="blue dim", align="left")
    console.print(f"[dim]Query:[/dim] [italic yellow]\"{query}\"[/italic yellow]\n")


def display_results(results: List[SearchResult]):
    if not results:
        console.print("[bold red]No results found.[/bold red]")
        return

    for res in results:
        # Title bar: [Index] Title (domain)
        title_text = Text()
        title_text.append(f"[{res.index}] ", style="bold magenta")
        title_text.append(
            res.title,
            style=Style(color="cyan", bold=True, underline=True, link=res.link),
        )
        if res.display_domain:
            title_text.append(f"  ({res.display_domain})", style="dim green")

        # Inner body with explicit double newlines for vertical breathing room
        content = Text()
        content.append(f"URL: {res.link}\n\n", style="dim blue underline")
        content.append(res.snippet, style="bright_white")

        panel = Panel(
            content,
            title=title_text,
            title_align="left",
            border_style="gray35",
            box=box.ROUNDED,
            expand=True,  # Allows the panel to fill full terminal width naturally
            padding=(1, 2),
        )
        console.print(panel)
        console.print()  # Space between panels


def prompt_interactive_selection(results: List[SearchResult]):
    if not results:
        return

    choices = [
        Choice(
            value=res.link,
            name=f"[{res.index}] {res.title[:70]}... ({res.display_domain})"
            if len(res.title) > 70
            else f"[{res.index}] {res.title} ({res.display_domain})",
        )
        for res in results
    ]
    choices.append(Choice(value=None, name="[Exit]"))

    try:
        selected_link = inquirer.select(
            message="Open in browser:",
            choices=choices,
            default=choices[0].value,
            pointer="❯",
            vi_mode=True,
        ).execute()

        if selected_link:
            console.print(f"\n[bold cyan]Opening:[/bold cyan] {selected_link}")
            webbrowser.open(selected_link)
        else:
            console.print("\n[dim]Exited.[/dim]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Exited.[/dim]")