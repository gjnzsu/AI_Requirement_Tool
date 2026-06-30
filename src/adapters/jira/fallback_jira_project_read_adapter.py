"""Fallback Jira read adapter that can use MCP before direct API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FallbackJiraProjectReadAdapter:
    """Read Jira issues through MCP when available, otherwise direct adapter."""

    SEARCH_TOOL_NAMES = (
        "searchJiraIssuesUsingJql",
        "search_jira_issues_using_jql",
        "searchJiraIssues",
        "jira_search_issues",
    )
    GET_TOOL_NAMES = ("getJiraIssue", "get_jira_issue", "jira_get_issue")
    COMMENT_TOOL_NAMES = (
        "getJiraIssueComments",
        "get_jira_issue_comments",
        "jira_get_issue_comments",
    )
    SPRINT_TOOL_NAMES = (
        "listJiraSprints",
        "list_jira_sprints",
        "getJiraSprints",
        "jira_list_sprints",
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

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        payload = self._invoke_first_tool(
            self.SEARCH_TOOL_NAMES,
            {"jql": jql, "maxResults": max_results, "max_results": max_results},
        )
        issues = self._extract_items(payload, "issues")
        if issues is not None:
            return issues
        if self.direct_adapter:
            return self.direct_adapter.search_issues(jql, max_results=max_results)
        return []

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        payload = self._invoke_first_tool(self.GET_TOOL_NAMES, {"issueKey": issue_key, "issue_key": issue_key})
        if isinstance(payload, dict):
            if isinstance(payload.get("issue"), dict):
                return payload["issue"]
            if payload.get("key") or payload.get("id"):
                return payload
        if self.direct_adapter:
            return self.direct_adapter.get_issue(issue_key)
        return None

    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        payload = self._invoke_first_tool(self.COMMENT_TOOL_NAMES, {"issueKey": issue_key, "issue_key": issue_key})
        comments = self._extract_items(payload, "comments")
        if comments is not None:
            return comments
        if self.direct_adapter:
            return self.direct_adapter.get_issue_comments(issue_key)
        issue = self.get_issue(issue_key) or {}
        return [{"body": comment} for comment in issue.get("comments", [])]

    def list_sprints(self, project_key: str, states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        selected_states = states or ["active", "closed"]
        payload = self._invoke_first_tool(
            self.SPRINT_TOOL_NAMES,
            {
                "projectKey": project_key,
                "project_key": project_key,
                "states": selected_states,
                "state": ",".join(selected_states),
            },
        )
        sprints = self._extract_items(payload, "sprints")
        if sprints is not None:
            return sprints
        if self.direct_adapter and hasattr(self.direct_adapter, "list_sprints"):
            return self.direct_adapter.list_sprints(project_key, states=selected_states)
        return []

    def _invoke_first_tool(self, names: tuple[str, ...], args: Dict[str, Any]) -> Any:
        if not (self.use_mcp and self.mcp_integration):
            return None
        if not getattr(self.mcp_integration, "_initialized", False):
            return None
        for name in names:
            tool = self.mcp_integration.get_tool(name)
            if tool:
                return tool.invoke(input=args)
        return None

    def _extract_items(self, payload: Any, key: str) -> Optional[List[Dict[str, Any]]]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return None
        value = payload.get(key) or payload.get("results") or payload.get("data")
        return value if isinstance(value, list) else None
