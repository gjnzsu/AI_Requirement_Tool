"""Centralized dependency composition for application services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from requests.auth import HTTPBasicAuth

from src.adapters.confluence import (
    DirectConfluencePageAdapter,
    DirectConfluenceReadAdapter,
    FallbackConfluencePageAdapter,
    FallbackConfluenceReadAdapter,
)
from src.adapters.evaluation import JiraEvaluationAdapter
from src.adapters.jira import (
    DirectJiraIssueAdapter,
    DirectJiraProjectReadAdapter,
    FallbackJiraIssueAdapter,
    FallbackJiraProjectReadAdapter,
)
from src.services.project_status_workflow_service import ProjectStatusWorkflowService
from src.services.requirement_evaluation_settings import RequirementEvaluationSettings
from src.services.requirement_workflow_service import RequirementWorkflowService


@dataclass
class ApplicationServices:
    """Composed application services and ports for the current runtime."""

    workflow_service: Optional[RequirementWorkflowService]
    jira_issue_port: Optional[Any]
    confluence_page_port: Optional[Any]
    jira_evaluation_port: Optional[Any]
    jira_project_read_port: Optional[Any] = None
    confluence_read_port: Optional[Any] = None
    project_status_workflow_service: Optional[ProjectStatusWorkflowService] = None
    rag_ingestion_port: Optional[Any] = None
    rag_query_port: Optional[Any] = None


def build_application_services(
    *,
    config: Any,
    llm_provider: Optional[Any],
    jira_tool: Optional[Any] = None,
    confluence_tool: Optional[Any] = None,
    jira_evaluator: Optional[Any] = None,
    rag_service: Optional[Any] = None,
    rag_ingestion_port: Optional[Any] = None,
    rag_query_port: Optional[Any] = None,
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

    direct_jira_read_adapter = (
        DirectJiraProjectReadAdapter(
            jira_tool,
            jira_url=getattr(config, "JIRA_URL", ""),
        )
        if jira_tool
        else None
    )
    jira_project_read_port = None
    if direct_jira_read_adapter or mcp_integration:
        jira_project_read_port = FallbackJiraProjectReadAdapter(
            direct_adapter=direct_jira_read_adapter,
            mcp_integration=mcp_integration,
            use_mcp=use_mcp,
        )

    confluence_auth = HTTPBasicAuth(
        getattr(config, "JIRA_EMAIL", ""),
        getattr(config, "JIRA_API_TOKEN", ""),
    )
    direct_confluence_read_adapter = (
        DirectConfluenceReadAdapter(
            confluence_url=getattr(config, "CONFLUENCE_URL", ""),
            auth=confluence_auth,
        )
        if getattr(config, "CONFLUENCE_URL", "")
        else None
    )
    confluence_read_port = None
    if direct_confluence_read_adapter or mcp_integration:
        confluence_read_port = FallbackConfluenceReadAdapter(
            direct_adapter=direct_confluence_read_adapter,
            mcp_integration=mcp_integration,
            use_mcp=use_mcp,
        )

    project_status_workflow_service = None
    if jira_project_read_port or confluence_read_port:
        project_status_workflow_service = ProjectStatusWorkflowService(
            jira_reader=jira_project_read_port,
            confluence_reader=confluence_read_port,
        )

    workflow_service = None
    if llm_provider and jira_issue_port:
        workflow_service = RequirementWorkflowService(
            llm_provider=llm_provider,
            jira_issue_port=jira_issue_port,
            jira_evaluation_port=jira_evaluation_port,
            confluence_page_port=confluence_page_port,
            rag_service=rag_ingestion_port if rag_ingestion_port is not None else rag_service,
            evaluation_settings=RequirementEvaluationSettings.from_config(config),
            confluence_space_key=getattr(config, "CONFLUENCE_SPACE_KEY", ""),
        )

    return ApplicationServices(
        workflow_service=workflow_service,
        jira_issue_port=jira_issue_port,
        confluence_page_port=confluence_page_port,
        jira_evaluation_port=jira_evaluation_port,
        jira_project_read_port=jira_project_read_port,
        confluence_read_port=confluence_read_port,
        project_status_workflow_service=project_status_workflow_service,
        rag_ingestion_port=rag_ingestion_port if rag_ingestion_port is not None else rag_service,
        rag_query_port=rag_query_port,
    )
