"""Opt-in real Jira E2E test for the pre-Jira quality gate workflow.

This test creates a real Jira issue. It is skipped unless RUN_REAL_JIRA_E2E=true.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from config.config import Config
from src.adapters.jira.direct_jira_issue_adapter import DirectJiraIssueAdapter
from src.services.requirement_evaluation_settings import RequirementEvaluationSettings
from src.services.requirement_workflow_service import RequirementWorkflowService
from src.tools.jira_tool import JiraTool


def _real_jira_e2e_enabled() -> bool:
    return os.getenv("RUN_REAL_JIRA_E2E", "false").lower() in {"true", "1", "yes"}


def _has_real_jira_config() -> bool:
    required = [
        Config.JIRA_URL,
        Config.JIRA_EMAIL,
        Config.JIRA_API_TOKEN,
        Config.JIRA_PROJECT_KEY,
    ]
    return all(value and not str(value).startswith("your-") for value in required)


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(120)
def test_real_jira_creation_runs_after_quality_gate_passes():
    if not _real_jira_e2e_enabled():
        pytest.skip("Set RUN_REAL_JIRA_E2E=true to create a real Jira issue.")
    if not _has_real_jira_config():
        pytest.skip("Real Jira configuration is missing or still using defaults.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    summary = f"[E2E][quality-gate] Login audit trail {timestamp}"
    backlog_data = {
        "summary": summary,
        "business_value": "Improves security traceability for production access reviews.",
        "acceptance_criteria": [
            "Given a successful login, when the login completes, then an audit event records user id, timestamp, and source IP.",
            "Given a failed login, when the failure occurs, then an audit event records the attempted user id, timestamp, source IP, and failure reason.",
        ],
        "priority": "Medium",
        "invest_analysis": "Independent, valuable, small enough to implement, and testable through audit log assertions.",
        "description": (
            "Business Value: Improves security traceability for production access reviews.\n\n"
            "Acceptance Criteria:\n"
            "- Successful logins record user id, timestamp, and source IP.\n"
            "- Failed logins record attempted user id, timestamp, source IP, and failure reason.\n\n"
            "INVEST: Independent, valuable, small, and testable."
        ),
    }

    service = RequirementWorkflowService(
        llm_provider=object(),
        jira_issue_port=DirectJiraIssueAdapter(JiraTool()),
        evaluation_settings=RequirementEvaluationSettings(
            evaluation_enabled=False,
            gate_enabled=True,
            judge_enabled=False,
        ),
    )

    result = service.execute_backlog_data(backlog_data)

    assert result.success is True, result.response_text
    assert result.jira_result is not None
    assert result.jira_result["key"]
    assert result.jira_result["link"]
    assert result.workflow_progress[0] == {
        "step": "quality_review",
        "label": "Review Quality",
        "status": "completed",
        "detail": "Deterministic checks passed.",
    }
    assert result.workflow_progress[1]["status"] == "completed"
    assert result.workflow_progress[2] == {
        "step": "evaluation",
        "label": "Evaluate Requirement",
        "status": "skipped",
        "detail": "Post-Jira maturity evaluation disabled by configuration.",
    }
