"""Adapter that evaluates created Jira issues through the maturity evaluator."""

from __future__ import annotations

from typing import Any, Dict


class JiraEvaluationAdapter:
    """Load a created Jira issue and run maturity evaluation against it."""

    def __init__(self, jira_evaluator: Any) -> None:
        self.jira_evaluator = jira_evaluator

    def load_issue(self, issue_key: str) -> Dict[str, Any]:
        issue = self.jira_evaluator.jira.issue(issue_key)
        return {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description or "",
            "status": issue.fields.status.name,
            "priority": issue.fields.priority.name if issue.fields.priority else "Unassigned",
        }

    def evaluate_issue(self, issue_key: str):
        return self.jira_evaluator.evaluate_maturity(self.load_issue(issue_key))

