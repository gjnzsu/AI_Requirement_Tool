from src.adapters.confluence import DirectConfluenceReadAdapter, FallbackConfluenceReadAdapter
from src.adapters.jira import DirectJiraProjectReadAdapter, FallbackJiraProjectReadAdapter


class FakeJiraIssue:
    def __init__(self, key="AIP-1", fields=None):
        self.key = key
        self.fields = fields or type(
            "Fields",
            (),
            {
                "summary": "Build PM Agent",
                "status": type("Status", (), {"name": "In Progress"})(),
                "assignee": type("Assignee", (), {"displayName": "Maya"})(),
                "priority": type("Priority", (), {"name": "High"})(),
                "duedate": "2026-06-22",
                "comment": type(
                    "CommentContainer",
                    (),
                    {"comments": [type("Comment", (), {"body": "No blocker"})()]},
                )(),
            },
        )()


class FakeJiraClient:
    def __init__(self):
        self.issue_obj = FakeJiraIssue()

    def search_issues(self, jql, maxResults=50):
        self.last_jql = jql
        self.last_max_results = maxResults
        return [self.issue_obj]

    def issue(self, issue_key):
        return FakeJiraIssue(key=issue_key)


class FakeJiraTool:
    def __init__(self):
        self.jira = FakeJiraClient()


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = "ok"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)

    def json(self):
        return self._payload


class FakeRequestsSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if "search" in url:
            return FakeResponse(
                {
                    "results": [
                        {
                            "content": {
                                "id": "123",
                                "title": "PM Status",
                                "_links": {"webui": "/wiki/spaces/PM/pages/123"},
                            },
                            "excerpt": "Daily status",
                        }
                    ]
                }
            )
        return FakeResponse(
            {
                "id": "123",
                "title": "PM Status",
                "_links": {"webui": "/wiki/spaces/PM/pages/123"},
                "body": {"storage": {"value": "<p>Green</p>"}},
            }
        )


class FakeMcpTool:
    def __init__(self, payload):
        self.payload = payload

    def invoke(self, input):
        self.last_input = input
        return self.payload


class FakeMcpIntegration:
    _initialized = True

    def __init__(self, tools):
        self.tools = tools

    def get_tool(self, name):
        return self.tools.get(name)


def test_direct_jira_project_read_adapter_normalizes_search_and_comments():
    adapter = DirectJiraProjectReadAdapter(FakeJiraTool(), jira_url="https://jira.example")

    issues = adapter.search_issues("project = AIP", max_results=10)

    assert issues == [
        {
            "key": "AIP-1",
            "summary": "Build PM Agent",
            "status": "In Progress",
            "status_category": "",
            "assignee": "Maya",
            "due_date": "2026-06-22",
            "priority": "High",
            "comments": ["No blocker"],
            "links": [],
            "url": "https://jira.example/browse/AIP-1",
        }
    ]
    assert adapter.get_issue("AIP-2")["key"] == "AIP-2"
    assert adapter.get_issue_comments("AIP-1") == [{"body": "No blocker"}]


def test_fallback_jira_project_read_adapter_uses_mcp_when_available():
    mcp = FakeMcpIntegration(
        {"searchJiraIssuesUsingJql": FakeMcpTool({"issues": [{"key": "AIP-9"}]})}
    )
    adapter = FallbackJiraProjectReadAdapter(mcp_integration=mcp, use_mcp=True)

    assert adapter.search_issues("project = AIP") == [{"key": "AIP-9"}]


def test_direct_confluence_read_adapter_normalizes_page_and_search_results():
    session = FakeRequestsSession()
    adapter = DirectConfluenceReadAdapter(
        confluence_url="https://example.atlassian.net/wiki",
        auth=("user", "token"),
        session=session,
    )

    page = adapter.get_page(page_id="123")
    pages = adapter.search_pages("PM Status", space_key="PM")

    assert page["id"] == "123"
    assert page["content"] == "Green"
    assert page["url"] == "https://example.atlassian.net/wiki/spaces/PM/pages/123"
    assert pages[0]["title"] == "PM Status"


def test_fallback_confluence_read_adapter_uses_mcp_when_available():
    mcp = FakeMcpIntegration(
        {"getConfluencePage": FakeMcpTool({"id": "123", "title": "PM Status", "content": "Green"})}
    )
    adapter = FallbackConfluenceReadAdapter(mcp_integration=mcp, use_mcp=True)

    assert adapter.get_page(page_id="123")["title"] == "PM Status"
