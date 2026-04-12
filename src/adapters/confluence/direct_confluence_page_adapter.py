"""Direct Confluence adapter backed by the custom Confluence tool."""

from __future__ import annotations

from typing import Any

from src.agent.confluence_nodes import create_confluence_page_via_direct_api
from src.application.ports.result_types import ConfluencePageResult


class DirectConfluencePageAdapter:
    """Create Confluence pages through the direct Confluence tool."""

    def __init__(self, confluence_tool: Any) -> None:
        self.confluence_tool = confluence_tool

    def create_page(self, page_title: str, confluence_content: str) -> ConfluencePageResult:
        result = create_confluence_page_via_direct_api(
            self.confluence_tool,
            page_title=page_title,
            confluence_content=confluence_content,
        )
        return ConfluencePageResult(
            success=bool(result.get("success")),
            page_id=str(result.get("id")) if result.get("id") is not None else None,
            title=result.get("title", page_title),
            link=result.get("link"),
            error=result.get("error"),
            tool_used=result.get("tool_used", "Direct API"),
            raw_result=result,
        )

