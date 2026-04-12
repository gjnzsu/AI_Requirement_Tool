from unittest.mock import Mock

from src.services.rag_ingestion_service import RagIngestionService


def test_simplify_confluence_content_preserves_core_searchable_fields():
    service = RagIngestionService(rag_service=None)

    simplified = service.simplify_confluence_content(
        issue_key="PROJ-123",
        backlog_data={
            "summary": "Improve login flow",
            "priority": "High",
            "business_value": "Reduce failed sign-ins",
            "acceptance_criteria": ["Users can recover passwords"],
        },
        evaluation={"overall_maturity_score": 84},
        confluence_link="https://wiki.example/pages/123",
    )

    assert "PROJ-123" in simplified
    assert "Improve login flow" in simplified
    assert "Priority: High" in simplified
    assert "Maturity Score: 84/100" in simplified


def test_ingest_uses_metadata_to_build_document_id():
    rag_service = Mock()
    rag_service.ingest_text.return_value = "jira_issue:PROJ-123"
    service = RagIngestionService(rag_service=rag_service)

    result = service.ingest(
        "jira text",
        {"type": "jira_issue", "key": "PROJ-123"},
    )

    assert result == "jira_issue:PROJ-123"
    rag_service.ingest_text.assert_called_once_with(
        "jira text",
        {"type": "jira_issue", "key": "PROJ-123"},
        document_id="jira_issue:PROJ-123",
    )
