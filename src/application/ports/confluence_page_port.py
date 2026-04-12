"""Port for Confluence page creation."""

from __future__ import annotations

from typing import Protocol

from .result_types import ConfluencePageResult


class ConfluencePagePort(Protocol):
    """Application-facing contract for Confluence page creation."""

    def create_page(self, page_title: str, confluence_content: str) -> ConfluencePageResult:
        """Create a Confluence page from normalized title/content input."""

