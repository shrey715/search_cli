from typing import Dict, Type
from search_cli.providers.base import BaseSearchProvider
from search_cli.providers.bing import BingProvider
from search_cli.providers.brave import BraveProvider
from search_cli.providers.duckduckgo import DuckDuckGoProvider
from search_cli.providers.google import GoogleProvider
from search_cli.providers.searxng import SearXNGProvider

REGISTRY: Dict[str, Type[BaseSearchProvider]] = {
    DuckDuckGoProvider().name: DuckDuckGoProvider,
    GoogleProvider().name: GoogleProvider,
    BingProvider().name: BingProvider,
    BraveProvider().name: BraveProvider,
    SearXNGProvider().name: SearXNGProvider,
}


def get_configured_providers() -> Dict[str, BaseSearchProvider]:
    """Returns initialized instances of all configured providers."""
    configured = {}
    for name, cls in REGISTRY.items():
        provider = cls()
        if provider.is_configured():
            configured[name] = provider
    return configured
