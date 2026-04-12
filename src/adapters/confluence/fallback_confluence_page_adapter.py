"""Fallback Confluence adapter that hides MCP-vs-direct transport behavior."""

from __future__ import annotations

from typing import Any, Optional

from src.agent.confluence_nodes import (
    initialize_confluence_mcp_integration,
    invoke_mcp_confluence_tool,
    select_mcp_confluence_tool,
)
from src.application.ports.result_types import ConfluencePageResult


class FallbackConfluencePageAdapter:
    """Try MCP first, then fall back to the direct Confluence adapter."""

    def __init__(
        self,
        *,
        confluence_url: str,
        space_key: str,
        direct_adapter: Optional[Any] = None,
        mcp_integration: Optional[Any] = None,
        use_mcp: bool = True,
        get_cloud_id=None,
        resolve_space_id=None,
        html_to_markdown=None,
        initialize_mcp_integration=initialize_confluence_mcp_integration,
        select_mcp_tool=select_mcp_confluence_tool,
        invoke_mcp_tool=invoke_mcp_confluence_tool,
    ) -> None:
        self.confluence_url = confluence_url
        self.space_key = space_key
        self.direct_adapter = direct_adapter
        self.mcp_integration = mcp_integration
        self.use_mcp = use_mcp
        self.get_cloud_id = get_cloud_id or (lambda: None)
        self.resolve_space_id = resolve_space_id or (lambda space_key, cloud_id: None)
        self.html_to_markdown = html_to_markdown or (lambda value: value)
        self.initialize_mcp_integration = initialize_mcp_integration
        self.select_mcp_tool = select_mcp_tool
        self.invoke_mcp_tool = invoke_mcp_tool

    def create_page(self, page_title: str, confluence_content: str) -> ConfluencePageResult:
        mcp_error = None
        if self.use_mcp and self.mcp_integration:
            if getattr(self.mcp_integration, "_initialized", False) or self.initialize_mcp_integration(
                self.mcp_integration,
                timeout_seconds=15.0,
            ):
                tool = self.select_mcp_tool(self.mcp_integration)
                if tool:
                    try:
                        result = self.invoke_mcp_tool(
                            tool,
                            page_title=page_title,
                            confluence_content=confluence_content,
                            confluence_url=self.confluence_url,
                            space_key=self.space_key,
                            get_cloud_id=self.get_cloud_id,
                            resolve_space_id=self.resolve_space_id,
                            html_to_markdown=self.html_to_markdown,
                            timeout_seconds=60.0,
                        )
                    except Exception as exc:
                        mcp_error = str(exc)
                    else:
                        if result:
                            return ConfluencePageResult(
                                success=bool(result.get("success")),
                                page_id=str(result.get("id")) if result.get("id") is not None else None,
                                title=result.get("title", page_title),
                                link=result.get("link"),
                                error=result.get("error"),
                                tool_used=result.get("tool_used", "MCP Protocol"),
                                raw_result=result,
                            )

        if self.direct_adapter:
            direct_result = self.direct_adapter.create_page(page_title, confluence_content)
            if isinstance(direct_result, ConfluencePageResult):
                if direct_result.tool_used is None:
                    direct_result.tool_used = "Direct API"
                return direct_result

            if isinstance(direct_result, dict):
                return ConfluencePageResult(
                    success=bool(direct_result.get("success", True)),
                    page_id=str(direct_result.get("id")) if direct_result.get("id") is not None else None,
                    title=direct_result.get("title", page_title),
                    link=direct_result.get("link"),
                    error=direct_result.get("error"),
                    tool_used=direct_result.get("tool_used", "Direct API"),
                    raw_result=direct_result,
                )

        return ConfluencePageResult(
            success=False,
            title=page_title,
            error=mcp_error or "Confluence tool is not configured.",
            tool_used="MCP Protocol" if mcp_error else "Unavailable",
            raw_result={"success": False, "error": mcp_error or "Confluence tool is not configured."},
        )
