"""Fallback Confluence read adapter that can use MCP before direct API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FallbackConfluenceReadAdapter:
    """Read Confluence pages through MCP when available, otherwise direct adapter."""

    GET_TOOL_NAMES = (
        "getConfluencePage",
        "get_confluence_page",
        "confluence_get_page",
        "read_confluence_page",
    )
    SEARCH_TOOL_NAMES = (
        "searchConfluencePages",
        "search_confluence_pages",
        "getPagesInConfluenceSpace",
        "confluence_search_pages",
    )

    def __init__(
        self,
        *,
        direct_adapter: Optional[Any] = None,
        mcp_integration: Optional[Any] = None,
        use_mcp: bool = True,
    ) -> None:
        self.direct_adapter = direct_adapter
        self.mcp_integration = mcp_integration
        self.use_mcp = use_mcp

    def get_page(
        self,
        page_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload = self._invoke_first_tool(
            self.GET_TOOL_NAMES,
            {"page_id": page_id, "pageId": page_id, "title": title},
        )
        if isinstance(payload, dict):
            return payload.get("page") if isinstance(payload.get("page"), dict) else payload
        if isinstance(payload, str):
            return {"content": payload}
        if self.direct_adapter:
            return self.direct_adapter.get_page(page_id=page_id, title=title)
        return None

    def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        payload = self._invoke_first_tool(
            self.SEARCH_TOOL_NAMES,
            {"query": query, "space_key": space_key, "spaceKey": space_key, "limit": limit},
        )
        pages = self._extract_items(payload)
        if pages is not None:
            return pages
        if self.direct_adapter:
            return self.direct_adapter.search_pages(query, space_key=space_key, limit=limit)
        return []

    def _invoke_first_tool(self, names: tuple[str, ...], args: Dict[str, Any]) -> Any:
        if not (self.use_mcp and self.mcp_integration):
            return None
        if not getattr(self.mcp_integration, "_initialized", False):
            return None
        clean_args = {key: value for key, value in args.items() if value is not None}
        for name in names:
            tool = self.mcp_integration.get_tool(name)
            if tool:
                return tool.invoke(input=clean_args)
        return None

    def _extract_items(self, payload: Any) -> Optional[List[Dict[str, Any]]]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return None
        value = payload.get("pages") or payload.get("results") or payload.get("data")
        return value if isinstance(value, list) else None
