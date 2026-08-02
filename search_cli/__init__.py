from typing import Dict, Type
from search_cli.providers.base import BaseSearchProvider

REGISTRY: Dict[str, Type[BaseSearchProvider]] = {}


def register_provider(cls: Type[BaseSearchProvider]):
    """Decorator to register a provider class dynamically."""
    instance = cls()
    REGISTRY[instance.name] = cls
    return cls


def get_configured_providers() -> Dict[str, BaseSearchProvider]:
    """Returns initialized instances of all configured providers."""
    configured = {}
    for name, cls in REGISTRY.items():
        provider = cls()
        if provider.is_configured():
            configured[name] = provider
    return configured
