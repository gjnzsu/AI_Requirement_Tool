"""Port for Jira project read operations used by PM status workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class JiraProjectReadPort(Protocol):
    """Application-facing contract for reading Jira project state."""

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Return Jira issues matching the provided JQL query."""

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Return one Jira issue by key, or None when it cannot be found."""

    def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """Return comments for the given Jira issue."""
