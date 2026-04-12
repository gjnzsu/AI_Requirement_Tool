from src.adapters.jira.fallback_jira_issue_adapter import FallbackJiraIssueAdapter


class FakeTool:
    def __init__(self, name="create_jira_issue"):
        self.name = name


class FakeMcpIntegration:
    def __init__(self, initialized=True):
        self._initialized = initialized


class FakeDirectAdapter:
    def __init__(self):
        self.calls = []

    def create_issue(self, backlog_data):
        self.calls.append(backlog_data)
        return {"source": "direct", "backlog_data": backlog_data}


def test_fallback_jira_issue_adapter_uses_mcp_result_before_direct_tool():
    direct_adapter = FakeDirectAdapter()
    tool = FakeTool()
    captured = {}

    adapter = FallbackJiraIssueAdapter(
        jira_url="https://jira.example",
        direct_adapter=direct_adapter,
        mcp_integration=FakeMcpIntegration(initialized=True),
        use_mcp=True,
        initialize_mcp_integration=lambda integration, timeout_seconds=30.0: True,
        select_mcp_tool=lambda integration: tool,
        invoke_mcp_tool=lambda selected_tool, *, backlog_data, jira_url, timeout_seconds=75.0: captured.update(
            {
                "tool": selected_tool,
                "backlog_data": backlog_data,
                "jira_url": jira_url,
            }
        )
        or {
            "success": True,
            "key": "PROJ-123",
            "link": "https://jira.example/browse/PROJ-123",
            "tool_used": "MCP Protocol",
        },
    )

    result = adapter.create_issue({"summary": "Add login audit trail"})

    assert result.success is True
    assert result.key == "PROJ-123"
    assert result.tool_used == "MCP Protocol"
    assert captured["tool"] is tool
    assert captured["jira_url"] == "https://jira.example"
    assert direct_adapter.calls == []


def test_fallback_jira_issue_adapter_falls_back_to_direct_when_mcp_returns_none():
    direct_adapter = FakeDirectAdapter()

    adapter = FallbackJiraIssueAdapter(
        jira_url="https://jira.example",
        direct_adapter=direct_adapter,
        mcp_integration=FakeMcpIntegration(initialized=True),
        use_mcp=True,
        initialize_mcp_integration=lambda integration, timeout_seconds=30.0: True,
        select_mcp_tool=lambda integration: FakeTool(),
        invoke_mcp_tool=lambda selected_tool, *, backlog_data, jira_url, timeout_seconds=75.0: None,
    )

    result = adapter.create_issue({"summary": "Fallback issue"})

    assert result.raw_result == {
        "source": "direct",
        "backlog_data": {"summary": "Fallback issue"},
    }
    assert result.tool_used == "Direct API"
    assert direct_adapter.calls == [{"summary": "Fallback issue"}]


def test_fallback_jira_issue_adapter_falls_back_to_direct_when_mcp_raises():
    direct_adapter = FakeDirectAdapter()

    adapter = FallbackJiraIssueAdapter(
        jira_url="https://jira.example",
        direct_adapter=direct_adapter,
        mcp_integration=FakeMcpIntegration(initialized=True),
        use_mcp=True,
        initialize_mcp_integration=lambda integration, timeout_seconds=30.0: True,
        select_mcp_tool=lambda integration: FakeTool(),
        invoke_mcp_tool=lambda selected_tool, *, backlog_data, jira_url, timeout_seconds=75.0: (_ for _ in ()).throw(
            RuntimeError("MCP timeout")
        ),
    )

    result = adapter.create_issue({"summary": "Fallback issue"})

    assert result.raw_result == {
        "source": "direct",
        "backlog_data": {"summary": "Fallback issue"},
    }
    assert result.tool_used == "Direct API"
    assert direct_adapter.calls == [{"summary": "Fallback issue"}]
