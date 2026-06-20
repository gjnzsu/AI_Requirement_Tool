from src.application.ports import ConfluenceReadPort, JiraProjectReadPort


class FakeJiraProjectReader:
    def search_issues(self, jql: str, max_results: int = 50):
        return [{"key": "AI-1", "summary": jql, "max_results": max_results}]

    def get_issue(self, issue_key: str):
        return {"key": issue_key, "status": "In Progress"}

    def get_issue_comments(self, issue_key: str):
        return [{"issue_key": issue_key, "body": "No blockers"}]


class FakeConfluenceReader:
    def get_page(self, page_id: str | None = None, title: str | None = None):
        return {"id": page_id, "title": title or "Status"}

    def search_pages(self, query: str, space_key: str | None = None, limit: int = 10):
        return [{"title": query, "space_key": space_key, "limit": limit}]


def test_jira_project_read_port_accepts_fake_implementation():
    reader = FakeJiraProjectReader()

    assert isinstance(reader, JiraProjectReadPort)
    assert reader.search_issues("project = AI")[0]["key"] == "AI-1"
    assert reader.get_issue("AI-1")["status"] == "In Progress"
    assert reader.get_issue_comments("AI-1")[0]["body"] == "No blockers"


def test_confluence_read_port_accepts_fake_implementation():
    reader = FakeConfluenceReader()

    assert isinstance(reader, ConfluenceReadPort)
    assert reader.get_page(page_id="123")["id"] == "123"
    assert reader.search_pages("daily status", space_key="PMO")[0]["space_key"] == "PMO"
