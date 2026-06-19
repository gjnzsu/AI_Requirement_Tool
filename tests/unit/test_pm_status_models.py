import pytest

from src.application.ports import (
    PmStatusReport,
    SourceReference,
    StatusItem,
    SuggestedConfluenceContent,
    SuggestedJiraUpdate,
)


def test_pm_status_report_normalizes_and_serializes():
    report = PmStatusReport(
        project_key=" ai ",
        project_name="AI Platform",
        time_window="2026-06-19",
        audience="steering committee",
        health=" green ",
        executive_summary="Launch remains on track.",
        progress=[
            "RAG ingestion completed",
            StatusItem(summary="Jira workflow validated", owner="PMO"),
        ],
        risks=[StatusItem(summary="Security review still open", severity="medium")],
        blockers=[],
        decisions_needed=["Confirm production launch window"],
        owner_gaps=["API owner missing for quota workstream"],
        next_actions=[StatusItem(summary="Book go/no-go review", owner="Alice", due_date="2026-06-20")],
        suggested_jira_updates=[
            SuggestedJiraUpdate(
                issue_key="AI-42",
                field="status",
                current_value="In Progress",
                suggested_value="Ready for Review",
                rationale="Acceptance criteria are complete.",
            )
        ],
        suggested_confluence_content=SuggestedConfluenceContent(
            title="AI Platform Daily Status",
            body_markdown="## Status\nGreen",
            space_key="PMO",
        ),
        stakeholder_update="AI Platform is green for the 2026-06-19 window.",
        source_references=[
            SourceReference(source_type="jira", key="AI-42", title="RAG ingestion", url="https://jira/browse/AI-42")
        ],
        confidence_notes=["Meeting notes are current through standup."],
    )

    payload = report.to_dict()

    assert report.project_key == "AI"
    assert report.health == "Green"
    assert payload["progress"][0]["summary"] == "RAG ingestion completed"
    assert payload["next_actions"][0]["owner"] == "Alice"
    assert payload["suggested_jira_updates"][0]["issue_key"] == "AI-42"
    assert payload["suggested_confluence_content"]["space_key"] == "PMO"
    assert payload["source_references"][0]["source_type"] == "jira"
    assert "## Health: Green" in report.to_markdown()


def test_pm_status_report_rejects_invalid_health():
    with pytest.raises(ValueError, match="health"):
        PmStatusReport(
            project_key="AI",
            project_name="AI Platform",
            time_window="today",
            audience="team",
            health="Blue",
            executive_summary="Invalid color",
        )
