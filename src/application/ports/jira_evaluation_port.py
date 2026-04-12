"""Port for Jira maturity evaluation."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class JiraEvaluationPort(Protocol):
    """Application-facing contract for evaluating created Jira issues."""

    def evaluate_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Return the maturity evaluation payload for the given issue key."""

