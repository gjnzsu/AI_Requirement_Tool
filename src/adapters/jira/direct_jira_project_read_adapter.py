"""Direct Jira read adapter for PM status workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class DirectJiraProjectReadAdapter:
    """Read Jira project signals through the configured Jira client/tool."""

    def __init__(self, jira_tool: Any, *, jira_url: str = "") -> None:
        self.jira_tool = jira_tool
        self.jira = getattr(jira_tool, "jira", jira_tool)
        self.jira_url = jira_url.rstrip("/")

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        issues = self.jira.search_issues(jql, maxResults=max_results)
        return [self._normalize_issue(issue) for issue in issues]

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        try:
            return self._normalize_issue(self.jira.issue(issue_key))
        except Exception:
            return None

    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        issue = self.get_issue(issue_key)
        if not issue:
            return []
        return [{"body": comment} for comment in issue.get("comments", [])]

    def _normalize_issue(self, issue: Any) -> Dict[str, Any]:
        if isinstance(issue, dict):
            key = issue.get("key", "")
            payload = dict(issue)
            payload.setdefault("comments", [])
            payload.setdefault("links", [])
            if key and self.jira_url:
                payload.setdefault("url", f"{self.jira_url}/browse/{key}")
            return payload

        fields = getattr(issue, "fields", None)
        key = str(getattr(issue, "key", ""))
        comments = self._extract_comments(getattr(fields, "comment", None))
        links = self._extract_links(getattr(fields, "issuelinks", []))
        payload = {
            "key": key,
            "summary": str(getattr(fields, "summary", "") or ""),
            "status": self._extract_name(getattr(fields, "status", None)),
            "status_category": self._extract_status_category(getattr(fields, "status", None)),
            "assignee": self._extract_display_name(getattr(fields, "assignee", None)),
            "due_date": getattr(fields, "duedate", None),
            "priority": self._extract_name(getattr(fields, "priority", None)),
            "comments": comments,
            "links": links,
        }
        if key and self.jira_url:
            payload["url"] = f"{self.jira_url}/browse/{key}"
        return payload

    def _extract_comments(self, comment_container: Any) -> List[str]:
        comments = getattr(comment_container, "comments", []) if comment_container else []
        normalized = []
        for comment in comments:
            if isinstance(comment, dict):
                body = comment.get("body", "")
            else:
                body = getattr(comment, "body", "")
            if str(body).strip():
                normalized.append(str(body).strip())
        return normalized

    def _extract_links(self, links: Any) -> List[Dict[str, str]]:
        normalized = []
        for link in links or []:
            outward = getattr(link, "outwardIssue", None)
            inward = getattr(link, "inwardIssue", None)
            linked_issue = outward or inward
            if linked_issue is None:
                continue
            normalized.append(
                {
                    "type": self._extract_name(getattr(link, "type", None)),
                    "key": str(getattr(linked_issue, "key", "")),
                    "summary": str(getattr(getattr(linked_issue, "fields", None), "summary", "") or ""),
                }
            )
        return normalized

    def _extract_status_category(self, status: Any) -> str:
        category = getattr(status, "statusCategory", None)
        return self._extract_name(category)

    def _extract_name(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, dict):
            return str(value.get("name", "") or "")
        return str(getattr(value, "name", "") or "")

    def _extract_display_name(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get("displayName") or value.get("name")
        return getattr(value, "displayName", None) or getattr(value, "name", None)
