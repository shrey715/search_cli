from typing import Dict, Type
from search_cli.providers.base import BaseSearchProvider
from search_cli.providers.duckduckgo import DuckDuckGoProvider
from search_cli.providers.google import GoogleProvider

REGISTRY: Dict[str, Type[BaseSearchProvider]] = {
    DuckDuckGoProvider().name: DuckDuckGoProvider,
    GoogleProvider().name: GoogleProvider,
}


def get_configured_providers() -> Dict[str, BaseSearchProvider]:
    """Returns initialized instances of all configured providers."""
    configured = {}
    for name, cls in REGISTRY.items():
        provider = cls()
        if provider.is_configured():
            configured[name] = provider
    return configured
