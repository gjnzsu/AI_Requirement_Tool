"""Unit tests for Jira creation node helper functions."""

import pytest

from src.agent.jira_nodes import (
    build_jira_creation_error_message,
    build_jira_creation_success_message,
    build_jira_rag_document,
    build_jira_rag_metadata,
    normalize_mcp_jira_result,
    select_mcp_jira_tool,
)


class FakeMcpTool:
    def __init__(self, name):
        self.name = name


class FakeMcpIntegration:
    def __init__(self, tools):
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._tools = tools

    def get_tool(self, tool_name):
        return self._tools_by_name.get(tool_name)

    def get_tools(self):
        return self._tools


@pytest.mark.unit
def test_select_mcp_jira_tool_prefers_jira_tools_and_excludes_confluence_tools():
    """Tool selection should never return Confluence-like tools for Jira creation."""
    issue_tool = FakeMcpTool("create_issue")
    integration = FakeMcpIntegration([
        FakeMcpTool("create_confluence_page"),
        issue_tool,
        FakeMcpTool("create_page"),
    ])

    assert select_mcp_jira_tool(integration) is issue_tool


@pytest.mark.unit
def test_normalize_mcp_jira_result_parses_json_strings_and_dicts():
    """MCP payload normalization should support JSON code blocks and dict responses."""
    jira_url = "https://jira.example"

    assert normalize_mcp_jira_result(
        """```json
        {"success": true, "ticket_id": "PROJ-123", "link": "https://jira.example/browse/PROJ-123"}
        ```""",
        jira_url=jira_url,
    ) == {
        "success": True,
        "key": "PROJ-123",
        "link": "https://jira.example/browse/PROJ-123",
        "created_by": "MCP_SERVER",
        "tool_used": "custom-jira-mcp-server",
    }

    assert normalize_mcp_jira_result(
        {"success": True, "issue_key": "PROJ-456"},
        jira_url=jira_url,
    ) == {
        "success": True,
        "key": "PROJ-456",
        "link": "https://jira.example/browse/PROJ-456",
        "created_by": "MCP_SERVER",
        "tool_used": "custom-jira-mcp-server",
    }


@pytest.mark.unit
def test_normalize_mcp_jira_result_raises_for_mcp_timeout_and_error_strings():
    """String error payloads should be surfaced as exceptions to trigger fallback."""
    with pytest.raises(ValueError, match="MCP tool timeout"):
        normalize_mcp_jira_result("request timed out", jira_url="https://jira.example")

    with pytest.raises(ValueError, match="MCP tool error"):
        normalize_mcp_jira_result("Error: invalid project", jira_url="https://jira.example")


@pytest.mark.unit
def test_build_jira_creation_messages_preserve_success_and_timeout_copy():
    """User-facing Jira messages should remain behavior-compatible."""
    assert build_jira_creation_success_message(
        "PROJ-123",
        "https://jira.example/browse/PROJ-123",
        "MCP Tool",
    ) == (
        "✅ Successfully created Jira issue: **PROJ-123**\n"
        "Link: https://jira.example/browse/PROJ-123\n\n"
        "_(Created using MCP Tool)_"
    )

    timeout_message = build_jira_creation_error_message("MCP tool timed out")
    generic_message = build_jira_creation_error_message("Permission denied")

    assert "Jira Creation Timeout" in timeout_message
    assert "Failed to create Jira issue" in generic_message


@pytest.mark.unit
def test_build_jira_rag_payloads_preserve_existing_document_shape():
    """RAG payload builders should keep the Jira issue content and metadata fields stable."""
    backlog_data = {
        "summary": "Add login auditing",
        "priority": "High",
        "business_value": "Improve security",
        "acceptance_criteria": ["Every login is recorded", "Exports are available"],
        "invest_analysis": "Independent and testable",
        "description": "Capture login events",
    }
    result = {
        "key": "PROJ-123",
        "link": "https://jira.example/browse/PROJ-123",
    }
    now = "2026-04-04T10:11:12"

    content = build_jira_rag_document(
        jira_result=result,
        backlog_data=backlog_data,
        tool_used="MCP Tool",
        created_at=now,
    )
    metadata = build_jira_rag_metadata(
        jira_result=result,
        backlog_data=backlog_data,
        created_at=now,
    )

    assert "Jira Issue: PROJ-123" in content
    assert "Acceptance Criteria: Every login is recorded, Exports are available" in content
    assert "Tool Used: MCP Tool" in content
    assert metadata == {
        "type": "jira_issue",
        "key": "PROJ-123",
        "title": "Add login auditing",
        "priority": "High",
        "link": "https://jira.example/browse/PROJ-123",
        "created_at": now,
    }
