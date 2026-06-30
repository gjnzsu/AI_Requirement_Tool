import json
from pathlib import Path

from src.services.project_status_workflow_service import ProjectStatusWorkflowService


FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "openspec"
    / "changes"
    / "archive"
    / "2026-06-19-add-pm-status-agent"
    / "test-data"
)


def _load_scenario(name: str) -> dict:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


class FakeJiraProjectReadPort:
    def __init__(self, issues: list[dict]):
        self.issues = issues
        self.seen_jqls = []

    def search_issues(self, jql: str, max_results: int = 50):
        self.seen_jqls.append(jql)
        return self.issues[:max_results]

    def get_issue(self, issue_key: str):
        for issue in self.issues:
            if issue["key"] == issue_key:
                return issue
        return None

    def get_issue_comments(self, issue_key: str):
        issue = self.get_issue(issue_key) or {}
        return [{"body": comment} for comment in issue.get("comments", [])]


class FakeConfluenceReadPort:
    def __init__(self, pages: list[dict]):
        self.pages = pages
        self.seen_space_keys = []

    def get_page(self, page_id: str | None = None, title: str | None = None):
        for page in self.pages:
            if page.get("id") == page_id or page.get("title") == title:
                return page
        return None

    def search_pages(self, query: str, space_key: str | None = None, limit: int = 10):
        self.seen_space_keys.append(space_key)
        return self.pages[:limit]


def test_project_status_workflow_generates_green_report_for_on_track_data():
    scenario = _load_scenario("scenario-01-on-track.json")
    report = ProjectStatusWorkflowService().generate_report_from_snapshot(scenario["input"])

    assert report.health == scenario["expected"]["health"]
    report_text = report.to_markdown()
    for phrase in scenario["expected"]["must_include"]:
        assert phrase in report_text
    for phrase in scenario["expected"]["must_not_include"]:
        assert phrase not in report_text


def test_project_status_workflow_generates_amber_report_for_delayed_data_without_blocker():
    scenario = _load_scenario("scenario-02-delayed-no-blocker.json")
    report = ProjectStatusWorkflowService().generate_report_from_snapshot(scenario["input"])

    assert report.health == scenario["expected"]["health"]
    report_text = report.to_markdown()
    for phrase in scenario["expected"]["must_include"]:
        assert phrase in report_text
    for phrase in scenario["expected"]["must_not_include"]:
        assert phrase not in report_text


def test_project_status_workflow_generates_red_report_for_delayed_data_with_blocker():
    scenario = _load_scenario("scenario-03-delayed-with-blocker.json")
    report = ProjectStatusWorkflowService().generate_report_from_snapshot(scenario["input"])

    assert report.health == scenario["expected"]["health"]
    report_text = report.to_markdown()
    for phrase in scenario["expected"]["must_include"]:
        assert phrase in report_text
    for phrase in scenario["expected"]["must_not_include"]:
        assert phrase not in report_text


def test_project_status_workflow_collects_project_data_through_read_ports():
    scenario = _load_scenario("scenario-02-delayed-no-blocker.json")
    input_data = scenario["input"]
    service = ProjectStatusWorkflowService(
        jira_reader=FakeJiraProjectReadPort(input_data["jira"]["issues"]),
        confluence_reader=FakeConfluenceReadPort(input_data["confluence"]["pages"]),
    )

    report = service.generate_report(
        project_key=input_data["project_key"],
        project_name=input_data["project_name"],
        time_window=input_data["time_window"],
        audience=input_data["audience"],
        jira_jql=input_data["jira"]["jql"],
        confluence_query="AI Platform",
        confluence_space_key="AIP",
        meeting_notes=input_data["meeting_notes"],
    )

    assert report.health == "Amber"
    assert "approval workflow slipped by two days" in report.to_markdown()
    assert service.confluence_reader.seen_space_keys == ["AIP"]


def test_project_status_workflow_collects_multiple_jira_queries_and_deduplicates_issues():
    class MultiQueryJiraReader(FakeJiraProjectReadPort):
        def search_issues(self, jql: str, max_results: int = 50):
            self.seen_jqls.append(jql)
            if "sprint in" in jql:
                return [
                    {"key": "AIP-1", "summary": "Active work", "status": "In Progress"},
                    {"key": "AIP-2", "summary": "Carry-over work", "status": "In Review"},
                ]
            return [
                {"key": "AIP-2", "summary": "Carry-over work", "status": "In Review"},
                {"key": "AIP-3", "summary": "Closed sprint context", "status": "Done"},
            ]

    jira_reader = MultiQueryJiraReader([])
    service = ProjectStatusWorkflowService(
        jira_reader=jira_reader,
        confluence_reader=FakeConfluenceReadPort([]),
    )

    report = service.generate_report(
        project_key="AIP",
        project_name="AIP Project",
        time_window="Current status",
        audience="Project stakeholders",
        jira_jql=[
            "project = AIP AND sprint in (101, 102)",
            "project = AIP AND sprint = 99",
        ],
        confluence_query="AIP",
        meeting_notes=[],
    )

    assert jira_reader.seen_jqls == [
        "project = AIP AND sprint in (101, 102)",
        "project = AIP AND sprint = 99",
    ]
    assert [ref.key for ref in report.source_references] == ["AIP-1", "AIP-2", "AIP-3"]


def test_project_status_workflow_green_summary_includes_jira_evidence():
    service = ProjectStatusWorkflowService()

    report = service.generate_report_from_snapshot(
        {
            "project_key": "AIP",
            "project_name": "AIP Project",
            "time_window": "Current status",
            "audience": "Project stakeholders",
            "jira": {
                "issues": [
                    {
                        "key": "AIP-1",
                        "summary": "Build checkout API",
                        "status": "In Progress",
                        "status_category": "In Progress",
                        "assignee": "Ada",
                    },
                    {
                        "key": "AIP-2",
                        "summary": "Payment callback",
                        "status": "Done",
                        "status_category": "Done",
                        "assignee": "Ben",
                    },
                    {
                        "key": "AIP-3",
                        "summary": "Release checklist",
                        "status": "To Do",
                        "status_category": "To Do",
                    },
                ]
            },
            "confluence": {"pages": []},
            "meeting_notes": [],
        }
    )

    report_text = report.to_markdown()

    assert report.health == "Green"
    assert "3 Jira issues" in report.executive_summary
    assert "1 in progress" in report.executive_summary
    assert "1 done" in report.executive_summary
    assert "1 without owner" in report.executive_summary
    assert "AIP-1 Build checkout API" in report.executive_summary
    assert "- Build checkout API: In Progress (source: AIP-1, owner: Ada)" in report_text


def test_project_status_workflow_done_blocker_does_not_drive_red_health():
    service = ProjectStatusWorkflowService()

    report = service.generate_report_from_snapshot(
        {
            "project_key": "AIPLAT",
            "project_name": "AIPLAT Project",
            "time_window": "Current status",
            "audience": "Project stakeholders",
            "jira": {
                "issues": [
                    {
                        "key": "AIPLAT-16",
                        "summary": "Retrieve grounded context for RAG queries",
                        "status": "Done",
                        "status_category": "Done",
                        "assignee": "Raymond Gao",
                        "comments": ["Previously blocked by security policy not approved."],
                    },
                    {
                        "key": "AIPLAT-46",
                        "summary": "RAG retrieval returns unauthorized chunks across knowledge domains",
                        "status": "In Review",
                        "status_category": "In Progress",
                        "assignee": "Raymond Gao",
                    },
                ]
            },
            "confluence": {
                "pages": [
                    {
                        "id": "24838146",
                        "title": "AIPLAT risks",
                        "content": (
                            "Risk: Security policy not approved and UAT readiness at risk; "
                            "escalation and owner decision required."
                        ),
                    }
                ]
            },
            "meeting_notes": [],
        }
    )

    report_text = report.to_markdown()

    assert report.health == "Amber"
    assert report.blockers == []
    assert "## Blockers" not in report_text
    assert "Resolved blocker: Retrieve grounded context for RAG queries: Done" in report_text
    assert "owner decision required for escalation path" not in report_text
    assert "escalation to accountable owners required today" not in report_text
