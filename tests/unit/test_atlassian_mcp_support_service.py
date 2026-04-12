import json
from unittest.mock import MagicMock

from src.services.atlassian_mcp_support_service import AtlassianMcpSupportService


class FakeConfig:
    JIRA_URL = "https://test.atlassian.net"
    JIRA_EMAIL = "test@example.com"
    JIRA_API_TOKEN = "test-token"
    CONFLUENCE_URL = "https://test.atlassian.net/wiki"


def test_get_cloud_id_prefers_accessible_resources_tool():
    mcp_integration = MagicMock()
    mcp_integration._initialized = True
    resources_tool = MagicMock()
    resources_tool.invoke.return_value = json.dumps(
        {"resources": [{"cloudId": "cloud-123"}]}
    )
    mcp_integration.get_tool.side_effect = (
        lambda name: resources_tool if name == "getAccessibleAtlassianResources" else None
    )

    service = AtlassianMcpSupportService(
        config=FakeConfig,
        mcp_integration=mcp_integration,
        use_mcp=True,
    )

    assert service.get_cloud_id() == "cloud-123"


def test_retrieve_confluence_page_info_parses_json_result_with_tool_marker():
    mcp_integration = MagicMock()
    mcp_integration._initialized = True
    get_page_tool = MagicMock()
    get_page_tool.name = "getConfluencePage"
    get_page_tool.invoke.return_value = json.dumps(
        {
            "success": True,
            "id": "12345",
            "title": "Test Page",
            "link": "https://test.atlassian.net/wiki/pages/12345",
        }
    )
    mcp_integration.get_tool.side_effect = (
        lambda name: get_page_tool if name == "getConfluencePage" else None
    )

    service = AtlassianMcpSupportService(
        config=FakeConfig,
        mcp_integration=mcp_integration,
        use_mcp=True,
    )

    result = service.retrieve_confluence_page_info(page_id="12345")

    assert result["success"] is True
    assert result["id"] == "12345"
    assert result["tool_used"] == "MCP Protocol"


def test_html_to_markdown_converts_basic_html_elements():
    service = AtlassianMcpSupportService(
        config=FakeConfig,
        mcp_integration=None,
        use_mcp=False,
    )

    markdown = service.html_to_markdown(
        '<h1>Title</h1><p><strong>Hello</strong> <a href="https://x">link</a></p>'
    )

    assert "# Title" in markdown
    assert "**Hello**" in markdown
    assert "[link](https://x)" in markdown
