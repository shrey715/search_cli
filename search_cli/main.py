import argparse
import sys
from dotenv import load_dotenv

# Load environment variables from .env, then let .env.local override them
load_dotenv()
load_dotenv(".env.local", override=True)

from search_cli.providers import get_configured_providers
from search_cli.tui import SearchApp
from search_cli.ui import console


def main():
    parser = argparse.ArgumentParser(
        description="Modular CLI Search Engine with Rich UI & Navigation",
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
        default="google",
        choices=["google", "duckduckgo"],
        help="Search provider backend to use",
    )
    parser.add_argument(
        "--max-results",
        "-n",
        type=int,
        default=10,
        help="Maximum number of search results to fetch",
    )

    args = parser.parse_args()
    query_str = " ".join(args.query)

    # Resolve configured search provider
    configured_providers = get_configured_providers()

    selected_provider_name = args.provider
    if selected_provider_name not in configured_providers:
        # Fall back gracefully to DuckDuckGo if Google keys are missing
        if "duckduckgo" in configured_providers:
            if selected_provider_name == "google":
                console.print(
                    "[yellow]Notice:[/yellow] Google API keys not found in .env. Falling back to [bold cyan]DuckDuckGo[/bold cyan].\n"
                )
            selected_provider_name = "duckduckgo"
        else:
            console.print("[bold red]Error:[/bold red] No search providers configured.")
            sys.exit(1)

    provider = configured_providers[selected_provider_name]

    # Perform initial search before entering the full-screen TUI
    try:
        with console.status(
            f"[bold green]Fetching results from {provider.display_name}...[/bold green]",
            spinner="dots",
        ):
            results = provider.search(query_str, max_results=args.max_results)
    except Exception as e:
        console.print(f"[bold red]Search error:[/bold red] {e}")
        sys.exit(1)

    # Hand off to the interactive, keybind-driven TUI
    app = SearchApp(
        query=query_str,
        results=results,
        provider=provider,
        providers=configured_providers,
        max_results=args.max_results,
    )
    app.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Aborted.[/dim]")
        sys.exit(0)
