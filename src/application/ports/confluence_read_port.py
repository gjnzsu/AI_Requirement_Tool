"""Port for Confluence read operations used by PM status workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ConfluenceReadPort(Protocol):
    """Application-facing contract for reading Confluence project context."""

    def get_page(
        self,
        page_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return a Confluence page by id or title, or None when it cannot be found."""

    def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return Confluence pages matching the search query."""
