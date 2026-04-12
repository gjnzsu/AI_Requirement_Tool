"""Port for Jira issue creation."""

from __future__ import annotations

from typing import Any, Dict, Protocol

from .result_types import JiraIssueResult


class JiraIssuePort(Protocol):
    """Application-facing contract for issue creation."""

    def create_issue(self, backlog_data: Dict[str, Any]) -> JiraIssueResult:
        """Create a Jira issue from normalized backlog data."""

