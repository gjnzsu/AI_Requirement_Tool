"""Deterministic pre-Jira requirement quality gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RequirementGateResult:
    blocked: bool
    blocking_reason: Optional[str] = None


class RequirementGateService:
    """Run narrow deterministic checks before durable workflow actions."""

    def evaluate(self, backlog_data: Dict[str, Any]) -> RequirementGateResult:
        criteria = backlog_data.get("acceptance_criteria")
        if isinstance(criteria, list) and any(str(item).strip() for item in criteria):
            return RequirementGateResult(blocked=False)

        return RequirementGateResult(
            blocked=True,
            blocking_reason=(
                "Requirement quality gate blocked creation because acceptance criteria are missing."
            ),
        )
