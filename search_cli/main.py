import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env, then let .env.local override them
load_dotenv()
load_dotenv(".env.local", override=True)

from search_cli.cache import ResultCache
from search_cli.config import load_config
from search_cli.config_cli import run_config_command
from search_cli.engine import perform_search
from search_cli.exporters import export_results
from search_cli.history import HistoryStore
from search_cli.providers import REGISTRY, get_configured_providers
from search_cli.tui import SearchApp
from search_cli.ui import console


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "config":
        run_config_command(sys.argv[2:])
        return

    config = load_config()
    configured_providers = get_configured_providers()
    if not configured_providers:
        console.print("[bold red]Error:[/bold red] No search providers configured.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Modular CLI Meta-Search Tool with a Full-Screen TUI",
        epilog="Run 'terch config' to view or edit the config file (~/.config/terch/config.toml) from the terminal.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "query",
        nargs="+",
        help="Search query terms",
    )
    parser.add_argument(
        "--provider",
        "-p",
        default=config.default_provider or "google",
        choices=list(REGISTRY.keys()),
        help="Search provider backend to use",
    )
    parser.add_argument(
        "--max-results",
        "-n",
        type=int,
        default=config.max_results,
        help="Maximum number of search results to fetch",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the on-disk result cache for this run",
    )
    parser.add_argument(
        "--export",
        metavar="PATH",
        help="Search, export results to PATH (.json or .md), and exit without opening the TUI",
    )

    args = parser.parse_args()
    query_str = " ".join(args.query)

    selected_provider_name = args.provider
    if selected_provider_name not in configured_providers:
        fallback_name = next(iter(configured_providers))
        console.print(
            f"[yellow]Notice:[/yellow] {selected_provider_name} isn't configured (missing API key?). "
            f"Falling back to [bold cyan]{configured_providers[fallback_name].display_name}[/bold cyan].\n"
        )
        selected_provider_name = fallback_name

    provider = configured_providers[selected_provider_name]

    cache = None if args.no_cache or not config.cache_enabled else ResultCache(ttl=config.cache_ttl)
    history = HistoryStore() if config.history_enabled else None

    # Perform initial search before entering the full-screen TUI
    try:
        with console.status(
            f"[bold green]Fetching results from {provider.display_name}...[/bold green]",
            spinner="dots",
        ):
            results = perform_search(
                provider, query_str, args.max_results, cache=cache, history=history
            )
    except Exception as e:
        console.print(f"[bold red]Search error:[/bold red] {e}")
        sys.exit(1)

    if args.export:
        export_results(results, Path(args.export))
        console.print(f"[bold green]Exported[/bold green] {len(results)} result(s) to {args.export}")
        return

    # Hand off to the interactive, keybind-driven TUI
    app = SearchApp(
        query=query_str,
        results=results,
        provider=provider,
        providers=configured_providers,
        max_results=args.max_results,
        cache=cache,
        history=history,
    )
    app.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Aborted.[/dim]")
        sys.exit(0)
