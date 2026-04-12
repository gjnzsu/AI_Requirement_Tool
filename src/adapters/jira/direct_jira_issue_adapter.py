"""Direct Jira adapter backed by the custom Jira tool."""

from __future__ import annotations

from typing import Any, Dict

from src.application.ports.result_types import JiraIssueResult


class DirectJiraIssueAdapter:
    """Create Jira issues through the direct Jira tool."""

    def __init__(self, jira_tool: Any) -> None:
        self.jira_tool = jira_tool

    def create_issue(self, backlog_data: Dict[str, Any]) -> JiraIssueResult:
        result = self.jira_tool.create_issue(
            summary=backlog_data.get("summary", "Untitled Issue"),
            description=backlog_data.get("description", ""),
            priority=backlog_data.get("priority", "Medium"),
        )
        return JiraIssueResult(
            success=bool(result.get("success")),
            key=result.get("key"),
            link=result.get("link"),
            error=result.get("error"),
            tool_used=result.get("tool_used", "Direct API"),
            raw_result=result,
        )

