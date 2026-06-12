"""Opt-in external RAG pipeline E2E tests for Requirement Copilot.

The live pipeline test writes synthetic Jira/Confluence documents to ai-rag-service.
It is skipped unless RUN_REAL_RAG_PIPELINE_E2E=true.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from config.config import Config
from src.runtime import build_rag_ports
from src.services.requirement_evaluation_settings import RequirementEvaluationSettings
from src.services.requirement_workflow_service import RequirementWorkflowService


def _real_rag_pipeline_e2e_enabled() -> bool:
    return os.getenv("RUN_REAL_RAG_PIPELINE_E2E", "false").lower() in {
        "true",
        "1",
        "yes",
    }


def _has_external_rag_config() -> bool:
    base_url = getattr(Config, "AI_RAG_SERVICE_URL", "")
    return (
        getattr(Config, "RAG_PROVIDER", "embedded") == "external"
        and bool(base_url)
        and not str(base_url).startswith("your-")
    )


class FakeJiraIssuePort:
    def create_issue(self, backlog_data):
        return {
            "success": True,
            "key": "PROJ-RAG-E2E",
            "link": "https://jira.example/browse/PROJ-RAG-E2E",
        }


class FakeJiraEvaluationPort:
    def evaluate_issue(self, issue_key):
        return {
            "overall_maturity_score": 92,
            "strengths": ["Clear auditability outcome"],
            "weaknesses": [],
            "recommendations": [],
            "detailed_scores": {"testability": 95},
        }


class FakeConfluencePagePort:
    def create_page(self, page_title, confluence_content):
        return SimpleNamespace(
            success=True,
            page_id="rag-e2e-page",
            title=page_title,
            link="https://wiki.example/pages/rag-e2e-page",
            raw_result={
                "success": True,
                "id": "rag-e2e-page",
                "title": page_title,
                "link": "https://wiki.example/pages/rag-e2e-page",
            },
        )


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(120)
def test_real_external_rag_pipeline_retrieves_related_jira_and_confluence_context():
    if not _real_rag_pipeline_e2e_enabled():
        pytest.skip("Set RUN_REAL_RAG_PIPELINE_E2E=true to write to ai-rag-service.")
    if not _has_external_rag_config():
        pytest.skip("Set RAG_PROVIDER=external and AI_RAG_SERVICE_URL for ai-rag-service.")

    rag_ports = build_rag_ports(config=Config, embedded_rag_service=None)
    assert rag_ports.provider == "external"
    assert rag_ports.query_port is not None
    assert rag_ports.ingestion_port is not None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    issue_key = f"RAG-E2E-{timestamp}"
    page_id = f"rag-e2e-page-{timestamp}"
    jira_doc_id = rag_ports.ingestion_port.ingest(
        content=(
            f"Jira issue {issue_key}: implement login audit trail. "
            "Audit events must include user id, timestamp, source IP, and outcome."
        ),
        metadata={
            "type": "jira_issue",
            "key": issue_key,
            "title": "Implement login audit trail",
            "url": f"https://jira.example/browse/{issue_key}",
            "project_key": "RAG",
            "status": "To Do",
            "priority": "Medium",
        },
    )
    confluence_doc_id = rag_ports.ingestion_port.ingest(
        content=(
            f"Confluence page for {issue_key}: design notes for login audit trail. "
            "The implementation validates audit retention and searchability."
        ),
        metadata={
            "type": "confluence_page",
            "title": f"{issue_key}: Login audit trail design",
            "url": f"https://wiki.example/pages/{page_id}",
            "page_id": page_id,
            "space_key": getattr(Config, "CONFLUENCE_SPACE_KEY", "RAG"),
            "related_jira": issue_key,
        },
    )

    assert jira_doc_id == f"jira_issue:{issue_key}"
    assert confluence_doc_id == f"confluence_page:{page_id}"

    jira_context = rag_ports.query_port.get_jira_context(issue_key)
    assert jira_context
    assert issue_key in jira_context
    assert "login audit trail" in jira_context.lower()
    assert "design notes" in jira_context.lower()

    confluence_chunks = rag_ports.query_port.retrieve(
        "login audit trail design",
        top_k=5,
        filters={"related_jira": issue_key, "type": "confluence_page"},
    )
    assert any(
        chunk.get("metadata", {}).get("related_jira") == issue_key
        for chunk in confluence_chunks
    )


@pytest.mark.e2e
@pytest.mark.integration
def test_external_rag_failure_does_not_block_requirement_workflow():
    unavailable_rag_ports = build_rag_ports(
        config=SimpleNamespace(
            RAG_PROVIDER="external",
            AI_RAG_SERVICE_URL="http://127.0.0.1:9",
            AI_RAG_SERVICE_TIMEOUT_SECONDS=0.1,
        ),
        embedded_rag_service=None,
    )
    service = RequirementWorkflowService(
        llm_provider=object(),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=FakeConfluencePagePort(),
        rag_service=unavailable_rag_ports.ingestion_port,
        evaluation_settings=RequirementEvaluationSettings(
            evaluation_enabled=True,
            gate_enabled=False,
            judge_enabled=False,
        ),
        confluence_space_key="RAG",
    )

    result = service.execute_backlog_data(
        {
            "summary": "Implement login audit trail",
            "business_value": "Improves security traceability.",
            "acceptance_criteria": ["Audit events are recorded for every login."],
            "priority": "Medium",
            "invest_analysis": "Small and testable.",
            "description": "Business Value: Improves security traceability.",
        }
    )

    assert result.success is True
    assert result.workflow_progress[0]["step"] == "quality_review"
    assert result.workflow_progress[0]["status"] == "skipped"
    assert result.workflow_progress[1]["status"] == "completed"
    assert result.workflow_progress[2]["status"] == "completed"
    assert result.workflow_progress[3]["status"] == "completed"
    assert result.workflow_progress[4] == {
        "step": "rag",
        "label": "Ingest to RAG",
        "status": "failed",
        "detail": "RAG ingestion did not return a document id.",
    }
