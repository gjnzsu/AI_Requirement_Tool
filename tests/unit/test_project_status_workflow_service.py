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

    def search_issues(self, jql: str, max_results: int = 50):
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
