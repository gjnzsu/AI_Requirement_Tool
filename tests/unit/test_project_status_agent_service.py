from src.services.project_status_agent_service import ProjectStatusAgentService
from src.services.project_status_workflow_service import ProjectStatusWorkflowService
from src.application.ports import ConfluencePageResult, PmStatusReport, SuggestedConfluenceContent


def test_pm_status_demo_scenarios_are_available_in_runtime_source():
    from src.services.pm_status_demo_scenarios import PM_STATUS_DEMO_SCENARIOS

    assert set(PM_STATUS_DEMO_SCENARIOS) == {
        "scenario-01-on-track",
        "scenario-02-delayed-no-blocker",
        "scenario-03-delayed-with-blocker",
    }
    assert PM_STATUS_DEMO_SCENARIOS["scenario-01-on-track"]["input"]["project_key"] == "AIP"


class FakeJiraReader:
    def __init__(self, sprints=None):
        self.seen_searches = []
        self.sprints = sprints

    def search_issues(self, jql: str, max_results: int = 50):
        self.seen_searches.append({"jql": jql, "max_results": max_results})
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

    def list_sprints(self, project_key: str, states=None):
        if self.sprints is None:
            raise NotImplementedError("Sprint metadata unavailable")
        return self.sprints


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
    jira_reader = FakeJiraReader(sprints=None)
    confluence_reader = FakeConfluenceReader()
    workflow = ProjectStatusWorkflowService(
        jira_reader=jira_reader,
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
    assert jira_reader.seen_searches == [
        {
            "jql": "project = AIP AND sprint in openSprints() ORDER BY priority DESC, updated DESC",
            "max_results": 50,
        }
    ]
    assert confluence_reader.seen_space_keys == [None]


def test_project_status_agent_service_analyzes_active_sprints_and_latest_closed_sprint():
    jira_reader = FakeJiraReader(
        sprints=[
            {"id": 101, "name": "Sprint 10", "state": "active", "startDate": "2026-06-20T00:00:00.000Z"},
            {"id": 102, "name": "Sprint 11", "state": "active", "startDate": "2026-06-24T00:00:00.000Z"},
            {
                "id": 99,
                "name": "Sprint 9",
                "state": "closed",
                "completeDate": "2026-06-19T12:00:00.000Z",
            },
            {
                "id": 98,
                "name": "Sprint 8",
                "state": "closed",
                "completeDate": "2026-06-12T12:00:00.000Z",
            },
        ]
    )
    workflow = ProjectStatusWorkflowService(
        jira_reader=jira_reader,
        confluence_reader=FakeConfluenceReader(),
    )
    service = ProjectStatusAgentService(workflow_service=workflow)

    service.handle_turn(
        user_input="Generate PM status for AIP for the weekly review",
        conversation_history=[],
        pending_state=None,
    )

    assert jira_reader.seen_searches == [
        {
            "jql": "project = AIP AND sprint in (101, 102) ORDER BY priority DESC, updated DESC",
            "max_results": 50,
        },
        {
            "jql": "project = AIP AND sprint = 99 ORDER BY priority DESC, updated DESC",
            "max_results": 50,
        },
    ]


def test_project_status_agent_service_uses_latest_closed_sprint_when_no_active_sprint():
    jira_reader = FakeJiraReader(
        sprints=[
            {
                "id": 201,
                "name": "Sprint 20",
                "state": "closed",
                "completeDate": "2026-06-26T12:00:00.000Z",
            },
            {
                "id": 200,
                "name": "Sprint 19",
                "state": "closed",
                "completeDate": "2026-06-19T12:00:00.000Z",
            },
        ]
    )
    workflow = ProjectStatusWorkflowService(
        jira_reader=jira_reader,
        confluence_reader=FakeConfluenceReader(),
    )
    service = ProjectStatusAgentService(workflow_service=workflow)

    service.handle_turn(
        user_input="Generate PM status for AIP",
        conversation_history=[],
        pending_state=None,
    )

    assert jira_reader.seen_searches == [
        {
            "jql": "project = AIP AND sprint = 201 ORDER BY priority DESC, updated DESC",
            "max_results": 50,
        }
    ]


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


def test_project_status_agent_service_parses_quoted_jira_project_key():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        default_project_key="DEFAULT",
    )

    result = service.handle_turn(
        user_input='pls help to give me the pm status of jira project "AIPLAT"',
        conversation_history=[],
        pending_state=None,
    )

    assert result.workflow_result.project_key == "AIPLAT"


def test_project_status_agent_service_does_not_treat_status_as_project_key():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        default_project_key="AIP",
    )

    result = service.handle_turn(
        user_input="please generate project status report",
        conversation_history=[],
        pending_state=None,
    )

    assert result.workflow_result.project_key == "AIP"
    assert "# AIP Project Status" in result.response_text
    assert "STATUS Project" not in result.response_text


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


def test_project_status_agent_service_approve_publishes_full_report_with_timestamped_title():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    confluence_page_port = FakeConfluencePagePort()
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        confluence_page_port=confluence_page_port,
        timestamp_provider=lambda: "2026-06-24 15:30:00 UTC",
    )
    report = PmStatusReport(
        project_key="AIP",
        project_name="AIP Project",
        time_window="This week",
        audience="Weekly Delivery Review",
        health="Green",
        executive_summary="MVP remains on track.",
        progress=["Gateway API is in review."],
        risks=["Approval workflow has limited test coverage."],
        blockers=["Security policy sign-off is pending."],
        decisions_needed=["Confirm launch readiness by Friday."],
        owner_gaps=["Release owner missing for rollout checklist."],
        next_actions=["Maya to close gateway review."],
        stakeholder_update="Delivery remains on track with one policy dependency.",
        suggested_confluence_content=SuggestedConfluenceContent(
            title="AIP Project - PM Status Update",
            body_markdown="## Health\nGreen",
        ),
    )
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "report": report.to_dict(),
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
    assert confluence_page_port.created_pages[0]["title"] == (
        "AIP Project - PM Status Update - 2026-06-24 15:30:00 UTC"
    )
    created_content = confluence_page_port.created_pages[0]["content"]
    assert "# AIP Project Status" in created_content
    assert "## Blockers" in created_content
    assert "Security policy sign-off is pending." in created_content
    assert "## Stakeholder Update" in created_content
    assert "https://example.atlassian.net/wiki/pages/999" in result.response_text


def test_project_status_agent_service_approve_timestamps_legacy_pending_content():
    workflow = ProjectStatusWorkflowService(
        jira_reader=FakeJiraReader(),
        confluence_reader=FakeConfluenceReader(),
    )
    confluence_page_port = FakeConfluencePagePort()
    service = ProjectStatusAgentService(
        workflow_service=workflow,
        confluence_page_port=confluence_page_port,
        timestamp_provider=lambda: "2026-06-24 15:31:00 UTC",
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
    assert confluence_page_port.created_pages == [
        {
            "title": "AIP Project - PM Status Update - 2026-06-24 15:31:00 UTC",
            "content": "## Health\nGreen",
        }
    ]


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
