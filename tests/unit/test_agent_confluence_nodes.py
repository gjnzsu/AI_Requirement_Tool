"""Unit tests for Confluence creation node helper functions."""

import pytest

from src.agent.confluence_nodes import (
    build_confluence_mcp_args,
    build_confluence_duplicate_result,
    build_confluence_error_message,
    build_confluence_page_link,
    build_confluence_rag_metadata,
    build_confluence_success_message,
    create_confluence_page_via_direct_api,
    detect_confluence_error_code,
    extract_confluence_tool_schema,
    initialize_confluence_mcp_integration,
    is_confluence_tool_name,
    is_rovo_confluence_tool,
    invoke_mcp_confluence_tool,
    normalize_mcp_confluence_result,
    normalize_mcp_confluence_dict_result,
    normalize_mcp_confluence_text_result,
    select_mcp_confluence_tool,
)


@pytest.mark.unit
def test_build_confluence_page_link_handles_webui_paths_page_ids_and_explicit_links():
    """Link builder should normalize Confluence Cloud webui paths and fallback pageId URLs."""
    base_url = "https://example.atlassian.net/wiki"

    assert build_confluence_page_link(base_url, explicit_link="https://custom/link") == "https://custom/link"
    assert build_confluence_page_link(base_url, webui_path="/spaces/TEAM/pages/123/Plan") == (
        "https://example.atlassian.net/wiki/spaces/TEAM/pages/123/Plan"
    )
    assert build_confluence_page_link(base_url, page_id="123") == (
        "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123"
    )


@pytest.mark.unit
def test_normalize_mcp_confluence_text_result_parses_successful_text_payloads():
    """Text MCP responses with created/pageId/url data should normalize to a success payload."""
    result = normalize_mcp_confluence_text_result(
        "Page created successfully. pageId=123 https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123",
        page_title="Release Plan",
        confluence_url="https://example.atlassian.net/wiki",
    )

    assert result == {
        "success": True,
        "id": "123",
        "title": "Release Plan",
        "link": "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123",
        "tool_used": "MCP Protocol",
    }


@pytest.mark.unit
def test_normalize_mcp_confluence_dict_result_supports_rovo_and_custom_shapes():
    """Dict normalization should accept both root-level ids and _links.webui paths."""
    rovo_result = normalize_mcp_confluence_dict_result(
        {
            "id": 456,
            "title": "Architecture",
            "_links": {"webui": "/spaces/ENG/pages/456/Architecture"},
        },
        page_title="Fallback Title",
        confluence_url="https://example.atlassian.net/wiki",
    )
    custom_result = normalize_mcp_confluence_dict_result(
        {
            "success": True,
            "pageId": "789",
            "title": "Runbook",
        },
        page_title="Fallback Title",
        confluence_url="https://example.atlassian.net/wiki",
    )

    assert rovo_result["success"] is True
    assert rovo_result["id"] == "456"
    assert rovo_result["link"] == "https://example.atlassian.net/wiki/spaces/ENG/pages/456/Architecture"
    assert custom_result["id"] == "789"
    assert custom_result["link"] == "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=789"


@pytest.mark.unit
def test_normalize_mcp_confluence_dict_result_raises_on_error_payloads():
    """Error dicts should surface a readable failure message for fallback handling."""
    with pytest.raises(ValueError, match="MCP tool error"):
        normalize_mcp_confluence_dict_result(
            {"success": False, "error": True, "error_type": "validation"},
            page_title="Release Plan",
            confluence_url="https://example.atlassian.net/wiki",
        )


@pytest.mark.unit
def test_build_confluence_messages_and_metadata_preserve_existing_copy():
    """Success, duplicate fallback, metadata, and error messages should stay behavior-compatible."""
    success_message = build_confluence_success_message(
        {"title": "Release Plan", "link": "https://wiki/page"},
        "Direct API",
    )
    duplicate_result = build_confluence_duplicate_result("Release Plan")
    metadata = build_confluence_rag_metadata(
        page_title="Release Plan",
        issue_key="PROJ-123",
        confluence_result={"id": "456", "link": "https://wiki/page"},
        created_at="2026-04-05T10:11:12",
    )
    timeout_message = build_confluence_error_message(
        error_code="TIMEOUT",
        tool_used="MCP Protocol",
        space_key="TEAM",
    )

    assert "Confluence Page Created (via Direct API)" in success_message
    assert duplicate_result == {
        "success": False,
        "error": 'Page with title "Release Plan" already exists. The MCP tool may have created it successfully, but we could not verify.',
        "tool_used": "Direct API (duplicate error)",
    }
    assert metadata == {
        "type": "confluence_page",
        "title": "Release Plan",
        "related_jira": "PROJ-123",
        "link": "https://wiki/page",
        "page_id": "456",
        "created_at": "2026-04-05T10:11:12",
    }
    assert "Confluence page creation failed (MCP Protocol)" in timeout_message


@pytest.mark.unit
def test_detect_confluence_error_code_maps_known_error_patterns():
    """Exception text detection should preserve the existing code mapping behavior."""
    assert detect_confluence_error_code("ConnectionResetError 10054") == "CONNECTION_RESET"
    assert detect_confluence_error_code("connection aborted by peer") == "CONNECTION_ABORTED"
    assert detect_confluence_error_code("request timeout") == "TIMEOUT"
    assert detect_confluence_error_code("401 unauthorized") == "AUTH_ERROR"
    assert detect_confluence_error_code("403 forbidden") == "PERMISSION_ERROR"
    assert detect_confluence_error_code("some other error") is None


class FakeMcpTool:
    def __init__(self, name, tool_schema=None, args_schema=None):
        self.name = name
        self._tool_schema = tool_schema
        self.args_schema = args_schema


class FakeMcpIntegration:
    def __init__(self, tools):
        self._tools_by_name = {tool.name: tool for tool in tools}
        self._tools = tools

    def get_tool(self, tool_name):
        return self._tools_by_name.get(tool_name)

    def get_tools(self):
        return self._tools


@pytest.mark.unit
def test_select_mcp_confluence_tool_prefers_confluence_and_excludes_jira_tools():
    """Confluence tool selection should ignore Jira/issue tools and prefer known names."""
    confluence_tool = FakeMcpTool("createConfluencePage")
    integration = FakeMcpIntegration([
        FakeMcpTool("create_jira_issue"),
        FakeMcpTool("createIssue"),
        confluence_tool,
    ])

    assert select_mcp_confluence_tool(integration) is confluence_tool


@pytest.mark.unit
def test_is_rovo_confluence_tool_detects_official_camel_case_tools():
    """Rovo detection should match official camelCase Confluence tools only."""
    assert is_rovo_confluence_tool("createConfluencePage") is True
    assert is_rovo_confluence_tool("create_confluence_page") is False
    assert is_rovo_confluence_tool("createJiraIssue") is False


@pytest.mark.unit
def test_extract_confluence_tool_schema_reads_private_schema_and_args_schema():
    """Schema extraction should support both _tool_schema and args_schema model_fields."""
    class FakeField:
        description = "Page title"

    class FakeArgsSchema:
        model_fields = {"title": FakeField()}

    private_schema_tool = FakeMcpTool("createConfluencePage", tool_schema={"inputSchema": {"properties": {"title": {"type": "string"}}}})
    args_schema_tool = FakeMcpTool("createConfluencePage", args_schema=FakeArgsSchema())

    assert extract_confluence_tool_schema(private_schema_tool) == {
        "inputSchema": {"properties": {"title": {"type": "string"}}}
    }
    assert extract_confluence_tool_schema(args_schema_tool) == {
        "inputSchema": {"properties": {"title": {"type": "string", "description": "Page title"}}}
    }


@pytest.mark.unit
def test_build_confluence_mcp_args_maps_schema_driven_rovo_parameters():
    """Schema-driven arg building should prefer markdown, cloudId, and stringified spaceId for Rovo."""
    tool_schema = {
        "inputSchema": {
            "properties": {
                "cloudId": {"type": "string"},
                "spaceId": {"type": "string"},
                "contentFormat": {"enum": ["markdown", "storage"]},
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["cloudId", "spaceId", "contentFormat", "title", "body"],
        }
    }

    args = build_confluence_mcp_args(
        tool_name="createConfluencePage",
        tool_schema=tool_schema,
        page_title="Release Plan",
        confluence_content="<p>HTML body</p>",
        markdown_content="Markdown body",
        space_key="TEAM",
        cloud_id="cloud-123",
        resolve_space_id=lambda _space_key, _cloud_id: 456,
    )

    assert args == {
        "cloudId": "cloud-123",
        "spaceId": "456",
        "contentFormat": "markdown",
        "title": "Release Plan",
        "body": "Markdown body",
    }


@pytest.mark.unit
def test_build_confluence_mcp_args_falls_back_to_generic_argument_set_without_schema():
    """No-schema tools should still get the broad fallback argument payload."""
    args = build_confluence_mcp_args(
        tool_name="create_confluence_page",
        tool_schema=None,
        page_title="Release Plan",
        confluence_content="<p>HTML body</p>",
        markdown_content="Markdown body",
        space_key="TEAM",
        cloud_id="cloud-123",
        resolve_space_id=lambda _space_key, _cloud_id: None,
    )

    assert args["title"] == "Release Plan"
    assert args["content"] == "<p>HTML body</p>"
    assert args["spaceKey"] == "TEAM"
    assert args["contentFormat"] == "markdown"
    assert args["cloudId"] == "cloud-123"


@pytest.mark.unit
def test_is_confluence_tool_name_rejects_jira_tools_and_accepts_confluence_tools():
    """Public tool-name guard should reject Jira tools while accepting valid Confluence ones."""
    assert is_confluence_tool_name("createConfluencePage") is True
    assert is_confluence_tool_name("create_confluence_page") is True
    assert is_confluence_tool_name("create_jira_issue") is False
    assert is_confluence_tool_name("createIssue") is False


@pytest.mark.unit
def test_normalize_mcp_confluence_result_handles_json_text_dict_and_invalid_types():
    """Raw MCP result normalization should collapse type-specific parsing into one helper."""
    json_result = normalize_mcp_confluence_result(
        """```json
        {"id": 123, "title": "Release Plan", "_links": {"webui": "/spaces/TEAM/pages/123/Release-Plan"}}
        ```""",
        page_title="Fallback Title",
        confluence_url="https://example.atlassian.net/wiki",
    )
    text_result = normalize_mcp_confluence_result(
        "created pageId=456 https://example.atlassian.net/wiki/pages/viewpage.action?pageId=456",
        page_title="Release Plan",
        confluence_url="https://example.atlassian.net/wiki",
    )
    dict_result = normalize_mcp_confluence_result(
        {"success": True, "pageId": "789", "title": "Runbook"},
        page_title="Fallback Title",
        confluence_url="https://example.atlassian.net/wiki",
    )

    assert json_result["id"] == "123"
    assert text_result["id"] == "456"
    assert dict_result["id"] == "789"

    with pytest.raises(ValueError, match="boolean"):
        normalize_mcp_confluence_result(
            True,
            page_title="Release Plan",
            confluence_url="https://example.atlassian.net/wiki",
        )


@pytest.mark.unit
def test_initialize_confluence_mcp_integration_initializes_uninitialized_integration():
    """Initialization helper should run the async initialize method and report readiness."""

    class FakeIntegration:
        def __init__(self):
            self._initialized = False

        async def initialize(self):
            self._initialized = True

    integration = FakeIntegration()

    assert initialize_confluence_mcp_integration(integration, timeout_seconds=1.0) is True
    assert integration._initialized is True


@pytest.mark.unit
def test_invoke_mcp_confluence_tool_builds_args_and_normalizes_result():
    """Invocation helper should build args, call the tool, and normalize the result payload."""

    captured = {}

    class FakeTool:
        name = "createConfluencePage"
        _tool_schema = {
            "inputSchema": {
                "properties": {
                    "cloudId": {"type": "string"},
                    "spaceId": {"type": "string"},
                    "contentFormat": {"enum": ["markdown", "storage"]},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["cloudId", "spaceId", "contentFormat", "title", "body"],
            }
        }

        def invoke(self, *, input):
            captured["input"] = input
            return {
                "success": True,
                "pageId": "456",
                "title": input["title"],
            }

    result = invoke_mcp_confluence_tool(
        FakeTool(),
        page_title="Release Plan",
        confluence_content="<p>HTML body</p>",
        confluence_url="https://example.atlassian.net/wiki",
        space_key="TEAM",
        get_cloud_id=lambda: "cloud-123",
        resolve_space_id=lambda _space_key, _cloud_id: 789,
        html_to_markdown=lambda value: f"md:{value}",
        timeout_seconds=1.0,
    )

    assert captured["input"] == {
        "cloudId": "cloud-123",
        "spaceId": "789",
        "contentFormat": "markdown",
        "title": "Release Plan",
        "body": "md:<p>HTML body</p>",
    }
    assert result == {
        "success": True,
        "id": "456",
        "title": "Release Plan",
        "link": "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=456",
        "tool_used": "MCP Protocol",
    }


@pytest.mark.unit
def test_create_confluence_page_via_direct_api_marks_success_and_duplicate_cases():
    """Direct API helper should preserve success tagging and duplicate-page fallback behavior."""

    class SuccessfulTool:
        def create_page(self, *, title, content):
            return {
                "success": True,
                "title": title,
                "link": f"https://wiki/{title}",
                "content": content,
            }

    class DuplicateTool:
        def create_page(self, *, title, content):
            raise RuntimeError(f'Page "{title}" already exists')

    success_result = create_confluence_page_via_direct_api(
        SuccessfulTool(),
        page_title="Release Plan",
        confluence_content="<p>HTML body</p>",
    )
    duplicate_result = create_confluence_page_via_direct_api(
        DuplicateTool(),
        page_title="Release Plan",
        confluence_content="<p>HTML body</p>",
    )

    assert success_result["success"] is True
    assert success_result["tool_used"] == "Direct API"
    assert duplicate_result == {
        "success": False,
        "error": 'Page with title "Release Plan" already exists. The MCP tool may have created it successfully, but we could not verify.',
        "tool_used": "Direct API (duplicate error)",
    }
