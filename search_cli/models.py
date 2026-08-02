from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """
    SearchResult entity to standardize the response for all the search API providers
    """

    title: str
    link: str
    snippet: str
    index: int = 0
    display_domain: Optional[str] = None

    def __post_init__(self):
        # Extract the domain for UI rendering if not provided
        if not self.display_domain and self.link:
            try:
                from urllib.parse import urlparse

                self.display_domain = urlparse(self.link).netloc
            except Exception:
                self.display_domain = ""
