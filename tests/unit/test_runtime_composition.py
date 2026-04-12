from src.runtime.composition import build_application_services


class FakeConfig:
    JIRA_URL = "https://jira.example"
    CONFLUENCE_URL = "https://example.atlassian.net/wiki"
    CONFLUENCE_SPACE_KEY = "TEAM"


class FakeJiraTool:
    pass


class FakeConfluenceTool:
    pass


class FakeEvaluator:
    pass


def test_build_application_services_returns_ports_and_workflow_service():
    services = build_application_services(
        config=FakeConfig,
        llm_provider=object(),
        jira_tool=FakeJiraTool(),
        confluence_tool=FakeConfluenceTool(),
        jira_evaluator=FakeEvaluator(),
        mcp_integration=None,
        use_mcp=False,
    )

    assert services.workflow_service is not None
    assert services.jira_issue_port is not None
    assert services.confluence_page_port is not None
    assert services.jira_evaluation_port is not None
