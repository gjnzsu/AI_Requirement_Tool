"""Centralized dependency composition for application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.adapters.confluence import (
    DirectConfluencePageAdapter,
    FallbackConfluencePageAdapter,
)
from src.adapters.evaluation import JiraEvaluationAdapter
from src.adapters.jira import DirectJiraIssueAdapter, FallbackJiraIssueAdapter
from src.services.requirement_workflow_service import RequirementWorkflowService


@dataclass
class ApplicationServices:
    """Composed application services and ports for the current runtime."""

    workflow_service: Optional[RequirementWorkflowService]
    jira_issue_port: Optional[Any]
    confluence_page_port: Optional[Any]
    jira_evaluation_port: Optional[Any]
    rag_ingestion_port: Optional[Any] = None


def build_application_services(
    *,
    config: Any,
    llm_provider: Optional[Any],
    jira_tool: Optional[Any] = None,
    confluence_tool: Optional[Any] = None,
    jira_evaluator: Optional[Any] = None,
    rag_service: Optional[Any] = None,
    mcp_integration: Optional[Any] = None,
    use_mcp: bool = True,
    get_cloud_id=None,
    resolve_space_id=None,
    html_to_markdown=None,
) -> ApplicationServices:
    """Assemble ports and application services in one place."""
    direct_jira_adapter = DirectJiraIssueAdapter(jira_tool) if jira_tool else None
    jira_issue_port = None
    if direct_jira_adapter or mcp_integration:
        jira_issue_port = FallbackJiraIssueAdapter(
            jira_url=getattr(config, "JIRA_URL", ""),
            direct_adapter=direct_jira_adapter,
            mcp_integration=mcp_integration,
            use_mcp=use_mcp,
        )

    direct_confluence_adapter = (
        DirectConfluencePageAdapter(confluence_tool) if confluence_tool else None
    )
    confluence_page_port = None
    if direct_confluence_adapter or mcp_integration:
        confluence_page_port = FallbackConfluencePageAdapter(
            confluence_url=getattr(config, "CONFLUENCE_URL", ""),
            space_key=getattr(config, "CONFLUENCE_SPACE_KEY", ""),
            direct_adapter=direct_confluence_adapter,
            mcp_integration=mcp_integration,
            use_mcp=use_mcp,
            get_cloud_id=get_cloud_id,
            resolve_space_id=resolve_space_id,
            html_to_markdown=html_to_markdown,
        )

    jira_evaluation_port = JiraEvaluationAdapter(jira_evaluator) if jira_evaluator else None

    workflow_service = None
    if llm_provider and jira_issue_port:
        workflow_service = RequirementWorkflowService(
            llm_provider=llm_provider,
            jira_issue_port=jira_issue_port,
            jira_evaluation_port=jira_evaluation_port,
            confluence_page_port=confluence_page_port,
            rag_service=rag_service,
        )

    return ApplicationServices(
        workflow_service=workflow_service,
        jira_issue_port=jira_issue_port,
        confluence_page_port=confluence_page_port,
        jira_evaluation_port=jira_evaluation_port,
    )
