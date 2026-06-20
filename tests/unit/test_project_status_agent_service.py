from src.services.project_status_agent_service import ProjectStatusAgentService
from src.services.project_status_workflow_service import ProjectStatusWorkflowService
from src.application.ports import ConfluencePageResult


def test_pm_status_demo_scenarios_are_available_in_runtime_source():
    from src.services.pm_status_demo_scenarios import PM_STATUS_DEMO_SCENARIOS

    assert set(PM_STATUS_DEMO_SCENARIOS) == {
        "scenario-01-on-track",
        "scenario-02-delayed-no-blocker",
        "scenario-03-delayed-with-blocker",
    }
    assert PM_STATUS_DEMO_SCENARIOS["scenario-01-on-track"]["input"]["project_key"] == "AIP"


class FakeJiraReader:
    def search_issues(self, jql: str, max_results: int = 50):
        return [
            {
                "key": "AIP-1",
                "summary": "Build Model Gateway API",
                "status": "In Review",
                "status_category": "In Progress",
                "assignee": "Maya",
                "due_date": "2026-06-22",
                "priority": "High",
                "comments": ["Dev complete. No blocker."],
                "links": [],
            }
        ]

    def get_issue(self, issue_key: str):
        return None

    def get_issue_comments(self, issue_key: str):
        return []


class FakeConfluenceReader:
    def __init__(self):
        self.seen_space_keys = []

    def search_pages(self, query: str, space_key: str | None = None, limit: int = 10):
        self.seen_space_keys.append(space_key)
        return [
            {
                "id": "123",
                "title": "AIP Delivery Plan",
                "content": "No open blockers. MVP remains on track.",
            }
        ]

    def get_page(self, page_id: str | None = None, title: str | None = None):
        return None


class FakeConfluencePagePort:
    def __init__(self):
        self.created_pages = []

    def create_page(self, page_title: str, confluence_content: str):
        self.created_pages.append(
            {"title": page_title, "content": confluence_content}
        )
        return ConfluencePageResult(
            success=True,
            page_id="999",
            title=page_title,
            link="https://example.atlassian.net/wiki/pages/999",
        )


def test_project_status_agent_service_handles_one_pm_status_turn():
    confluence_reader = FakeConfluenceReader()
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=confluence_reader,
    )
    service = ProjectStatusAgentService(workflow_service=workflow)

    result = service.handle_turn(
        user_input="Generate PM status for AIP for the weekly review",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "report"
    assert result.pending_state is None
    assert "Health: Green" in result.response_text
    assert "Build Model Gateway API" in result.response_text
    assert confluence_reader.seen_space_keys == [None]


def test_project_status_agent_service_parses_project_and_confluence_scope_from_conversation():
    confluence_reader = FakeConfluenceReader()
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=confluence_reader,
    )
    service = ProjectStatusAgentService(workflow_service=workflow)

    result = service.handle_turn(
        user_input="Generate PM status for Jira project AIP and Confluence space ENG",
        conversation_history=[],
        pending_state=None,
    )

    assert result.workflow_result.project_key == "AIP"
    assert result.workflow_result.project_name == "AIP Project"
    assert confluence_reader.seen_space_keys == ["ENG"]


def test_project_status_agent_service_uses_demo_scenario_without_live_readers():
    class FailingJiraReader:
        def search_issues(self, jql: str, max_results: int = 50):
            raise AssertionError("demo scenario should not call Jira")

    class FailingConfluenceReader:
        def search_pages(self, query: str, space_key: str | None = None, limit: int = 10):
            raise AssertionError("demo scenario should not call Confluence")

    workflow = ProjectStatusWorkflowService(
        jira_reader=FailingJiraReader(),
        confluence_reader=FailingConfluenceReader(),
    )
    service = ProjectStatusAgentService(workflow_service=workflow)

    result = service.handle_turn(
        user_input="Run PM demo scenario: scenario-03-delayed-with-blocker",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "report"
    assert result.workflow_result.health == "Red"
    assert "Security policy not approved" in result.response_text


def test_project_status_agent_service_suggests_write_back_without_creating_page():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    confluence_page_port = FakeConfluencePagePort()
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        confluence_page_port=confluence_page_port,
    )

    result = service.handle_turn(
        user_input="Generate PM status for AIP for the weekly review",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "confirmation"
    assert result.pending_state["awaiting_confirmation"] is True
    assert result.pending_state["suggested_confluence_content"]["title"] == "AIP Project - PM Status Update"
    assert confluence_page_port.created_pages == []
    assert "Reply with 'approve' to publish" in result.response_text


def test_project_status_agent_service_approve_publishes_only_pending_confluence_page():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    confluence_page_port = FakeConfluencePagePort()
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        confluence_page_port=confluence_page_port,
    )
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "suggested_confluence_content": {
            "title": "AIP Project - PM Status Update",
            "body_markdown": "## Health\nGreen",
        },
    }

    result = service.handle_turn(
        user_input="approve",
        conversation_history=[],
        pending_state=pending_state,
    )

    assert result.response_kind == "completed"
    assert result.pending_state is None
    assert confluence_page_port.created_pages == [
        {"title": "AIP Project - PM Status Update", "content": "## Health\nGreen"}
    ]
    assert "https://example.atlassian.net/wiki/pages/999" in result.response_text


def test_project_status_agent_service_cancel_does_not_write_back():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    confluence_page_port = FakeConfluencePagePort()
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        confluence_page_port=confluence_page_port,
    )
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "suggested_confluence_content": {
            "title": "AIP Project - PM Status Update",
            "body_markdown": "## Health\nGreen",
        },
    }

    result = service.handle_turn(
        user_input="cancel",
        conversation_history=[],
        pending_state=pending_state,
    )

    assert result.response_kind == "cancelled"
    assert result.pending_state is None
    assert confluence_page_port.created_pages == []
    assert "Nothing was published" in result.response_text
