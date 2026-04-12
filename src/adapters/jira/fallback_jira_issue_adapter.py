"""Fallback Jira adapter that hides MCP-vs-direct transport behavior."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.agent.jira_nodes import (
    initialize_jira_mcp_integration,
    invoke_mcp_jira_tool,
    select_mcp_jira_tool,
)
from src.application.ports.result_types import JiraIssueResult


class FallbackJiraIssueAdapter:
    """Try MCP first, then fall back to the direct Jira adapter."""

    def __init__(
        self,
        *,
        jira_url: str,
        direct_adapter: Optional[Any] = None,
        mcp_integration: Optional[Any] = None,
        use_mcp: bool = True,
        initialize_mcp_integration=initialize_jira_mcp_integration,
        select_mcp_tool=select_mcp_jira_tool,
        invoke_mcp_tool=invoke_mcp_jira_tool,
    ) -> None:
        self.jira_url = jira_url
        self.direct_adapter = direct_adapter
        self.mcp_integration = mcp_integration
        self.use_mcp = use_mcp
        self.initialize_mcp_integration = initialize_mcp_integration
        self.select_mcp_tool = select_mcp_tool
        self.invoke_mcp_tool = invoke_mcp_tool

    def create_issue(self, backlog_data: Dict[str, Any]) -> JiraIssueResult:
        mcp_error = None
        if self.use_mcp and self.mcp_integration:
            if getattr(self.mcp_integration, "_initialized", False) or self.initialize_mcp_integration(
                self.mcp_integration,
                timeout_seconds=30.0,
            ):
                tool = self.select_mcp_tool(self.mcp_integration)
                if tool:
                    try:
                        result = self.invoke_mcp_tool(
                            tool,
                            backlog_data=backlog_data,
                            jira_url=self.jira_url,
                            timeout_seconds=75.0,
                        )
                    except Exception as exc:
                        mcp_error = str(exc)
                    else:
                        if result:
                            return JiraIssueResult(
                                success=bool(result.get("success")),
                                key=result.get("key"),
                                link=result.get("link"),
                                error=result.get("error"),
                                tool_used=result.get("tool_used", "MCP Protocol"),
                                raw_result=result,
                            )

        if self.direct_adapter:
            direct_result = self.direct_adapter.create_issue(backlog_data)
            if isinstance(direct_result, JiraIssueResult):
                if direct_result.tool_used is None:
                    direct_result.tool_used = "Direct API"
                return direct_result

            if isinstance(direct_result, dict):
                return JiraIssueResult(
                    success=bool(direct_result.get("success", True)),
                    key=direct_result.get("key"),
                    link=direct_result.get("link"),
                    error=direct_result.get("error"),
                    tool_used=direct_result.get("tool_used", "Direct API"),
                    raw_result=direct_result,
                )

        return JiraIssueResult(
            success=False,
            error=mcp_error or "Jira tool is not configured. Please check your Jira credentials.",
            tool_used="MCP Protocol" if mcp_error else "Unavailable",
            raw_result={
                "success": False,
                "error": mcp_error or "Jira tool is not configured. Please check your Jira credentials.",
            },
        )
