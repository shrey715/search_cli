from abc import ABC, abstractmethod
from typing import List
from bs4 import BeautifulSoup
from search_cli.models import SearchResult


def strip_html(text: str) -> str:
    """Strip HTML highlight tags (e.g. <strong>) some APIs embed in snippets."""
    if not text:
        return text
    return BeautifulSoup(text, "html.parser").get_text()


class BaseSearchProvider(ABC):
    """
    Abstract class for all search providers (allows extensibility)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the providers (needed for referencing later on)"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name, need not be unique"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if required API keys / config environment variables exist."""
        pass

    @abstractmethod
    def search(self, query: str, max_results: int = 5, offset: int = 0) -> List[SearchResult]:
        """Perform search query and return standardized SearchResult items.

        `offset` is the number of results to skip (for pagination); each
        provider maps it onto whatever paging scheme its API actually uses.
        """
        pass
