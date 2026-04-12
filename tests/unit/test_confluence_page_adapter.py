from src.adapters.confluence.fallback_confluence_page_adapter import (
    FallbackConfluencePageAdapter,
)


class FakeTool:
    def __init__(self, name="createConfluencePage"):
        self.name = name


class FakeMcpIntegration:
    def __init__(self, initialized=True):
        self._initialized = initialized


class FakeDirectAdapter:
    def __init__(self):
        self.calls = []

    def create_page(self, page_title, confluence_content):
        self.calls.append((page_title, confluence_content))
        return {
            "source": "direct",
            "title": page_title,
            "content": confluence_content,
        }


def test_fallback_confluence_page_adapter_uses_mcp_before_direct_api():
    direct_adapter = FakeDirectAdapter()
    tool = FakeTool()
    captured = {}

    adapter = FallbackConfluencePageAdapter(
        confluence_url="https://example.atlassian.net/wiki",
        space_key="TEAM",
        direct_adapter=direct_adapter,
        mcp_integration=FakeMcpIntegration(initialized=True),
        use_mcp=True,
        get_cloud_id=lambda: "cloud-123",
        resolve_space_id=lambda space_key, cloud_id: 456,
        html_to_markdown=lambda html: f"md:{html}",
        initialize_mcp_integration=lambda integration, timeout_seconds=15.0: True,
        select_mcp_tool=lambda integration: tool,
        invoke_mcp_tool=lambda selected_tool, *, page_title, confluence_content, confluence_url, space_key, get_cloud_id, resolve_space_id, html_to_markdown, timeout_seconds=60.0: captured.update(
            {
                "tool": selected_tool,
                "title": page_title,
                "content": confluence_content,
                "confluence_url": confluence_url,
                "space_key": space_key,
            }
        )
        or {
            "success": True,
            "id": "456",
            "title": page_title,
            "link": "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=456",
            "tool_used": "MCP Protocol",
        },
    )

    result = adapter.create_page("Release Plan", "<p>Hello</p>")

    assert result.success is True
    assert result.page_id == "456"
    assert result.tool_used == "MCP Protocol"
    assert captured["tool"] is tool
    assert captured["space_key"] == "TEAM"
    assert direct_adapter.calls == []


def test_fallback_confluence_page_adapter_falls_back_to_direct_api_when_mcp_returns_none():
    direct_adapter = FakeDirectAdapter()

    adapter = FallbackConfluencePageAdapter(
        confluence_url="https://example.atlassian.net/wiki",
        space_key="TEAM",
        direct_adapter=direct_adapter,
        mcp_integration=FakeMcpIntegration(initialized=True),
        use_mcp=True,
        get_cloud_id=lambda: "cloud-123",
        resolve_space_id=lambda space_key, cloud_id: 456,
        html_to_markdown=lambda html: f"md:{html}",
        initialize_mcp_integration=lambda integration, timeout_seconds=15.0: True,
        select_mcp_tool=lambda integration: FakeTool(),
        invoke_mcp_tool=lambda selected_tool, *, page_title, confluence_content, confluence_url, space_key, get_cloud_id, resolve_space_id, html_to_markdown, timeout_seconds=60.0: None,
    )

    result = adapter.create_page("Release Plan", "<p>Hello</p>")

    assert result.raw_result == {
        "source": "direct",
        "title": "Release Plan",
        "content": "<p>Hello</p>",
    }
    assert result.tool_used == "Direct API"
    assert direct_adapter.calls == [("Release Plan", "<p>Hello</p>")]


def test_fallback_confluence_page_adapter_falls_back_to_direct_api_when_mcp_raises():
    direct_adapter = FakeDirectAdapter()

    adapter = FallbackConfluencePageAdapter(
        confluence_url="https://example.atlassian.net/wiki",
        space_key="TEAM",
        direct_adapter=direct_adapter,
        mcp_integration=FakeMcpIntegration(initialized=True),
        use_mcp=True,
        get_cloud_id=lambda: "cloud-123",
        resolve_space_id=lambda space_key, cloud_id: 456,
        html_to_markdown=lambda html: f"md:{html}",
        initialize_mcp_integration=lambda integration, timeout_seconds=15.0: True,
        select_mcp_tool=lambda integration: FakeTool(),
        invoke_mcp_tool=lambda selected_tool, *, page_title, confluence_content, confluence_url, space_key, get_cloud_id, resolve_space_id, html_to_markdown, timeout_seconds=60.0: (_ for _ in ()).throw(
            RuntimeError("MCP failure")
        ),
    )

    result = adapter.create_page("Release Plan", "<p>Hello</p>")

    assert result.raw_result == {
        "source": "direct",
        "title": "Release Plan",
        "content": "<p>Hello</p>",
    }
    assert result.tool_used == "Direct API"
    assert direct_adapter.calls == [("Release Plan", "<p>Hello</p>")]
