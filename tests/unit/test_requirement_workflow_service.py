import pytest

from src.services.requirement_workflow_service import RequirementWorkflowService


class FakeLLMProvider:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def generate_response(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeJiraIssue:
    key = "PROJ-123"

    class fields:
        summary = "Add login auditing"
        description = "Audit every login"

        class status:
            name = "To Do"

        class priority:
            name = "High"


class FakeEvaluator:
    def __init__(self, evaluation=None):
        self.jira = self
        self.evaluation = evaluation or {
            "overall_maturity_score": 90,
            "strengths": ["Clear business value"],
            "weaknesses": ["None"],
            "recommendations": ["Proceed to implementation"],
            "detailed_scores": {"clarity": 90},
        }

    def issue(self, issue_key):
        assert issue_key == "PROJ-123"
        return FakeJiraIssue()

    def evaluate_maturity(self, issue_dict):
        assert issue_dict["key"] == "PROJ-123"
        return self.evaluation


class FakeJiraTool:
    def __init__(self, result=None):
        self.result = result or {
            "success": True,
            "key": "PROJ-123",
            "link": "https://jira.example/browse/PROJ-123",
        }
        self.calls = []

    def create_issue(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class FakeConfluenceTool:
    def __init__(self, result=None):
        self.result = result or {
            "success": True,
            "title": "PROJ-123: Add login auditing",
            "link": "https://wiki.example/pages/123",
        }
        self.calls = []

    def create_page(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_execute_creates_jira_evaluates_and_creates_confluence():
    llm_provider = FakeLLMProvider(
        """
        ```json
        {
          "summary": "Add login auditing",
          "business_value": "Improves security traceability",
          "acceptance_criteria": ["Every login is recorded"],
          "priority": "High",
          "invest_analysis": "Small and testable",
          "description": "Business Value: Improves security traceability"
        }
        ```
        """
    )
    jira_tool = FakeJiraTool()
    confluence_tool = FakeConfluenceTool()

    service = RequirementWorkflowService(
        llm_provider=llm_provider,
        jira_tool=jira_tool,
        jira_evaluator=FakeEvaluator(),
        confluence_tool=confluence_tool,
    )

    result = service.execute(
        "create jira",
        [{"role": "user", "content": "Need login audit trail"}],
    )

    assert result.success is True
    assert result.jira_result["key"] == "PROJ-123"
    assert result.confluence_result["success"] is True
    assert jira_tool.calls == [
        {
            "summary": "Add login auditing",
            "description": "Business Value: Improves security traceability",
            "priority": "High",
        }
    ]
    assert confluence_tool.calls[0]["title"] == "PROJ-123: Add login auditing"
    assert "Successfully created Jira issue" in result.response_text
    assert "Maturity Evaluation Results" in result.response_text
    assert "Confluence Page Created" in result.response_text


def test_execute_returns_failure_when_backlog_json_is_invalid():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("not-json"),
        jira_tool=FakeJiraTool(),
    )

    result = service.execute("create jira", [])

    assert result.success is False
    assert result.jira_result is None
    assert "Error processing Jira creation request" in result.response_text


def test_execute_returns_failure_when_jira_creation_fails():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider(
            '{"summary": "Bad issue", "description": "desc", "priority": "Medium"}'
        ),
        jira_tool=FakeJiraTool(result={"success": False, "error": "Jira unavailable"}),
    )

    result = service.execute("create jira", [])

    assert result.success is False
    assert result.jira_result == {"success": False, "error": "Jira unavailable"}
    assert "Failed to create Jira issue: Jira unavailable" in result.response_text


def test_execute_preserves_jira_success_when_confluence_creation_fails():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider(
            '{"summary": "Add reporting", "business_value": "Visibility", '
            '"acceptance_criteria": ["Reports exist"], "priority": "Medium", '
            '"invest_analysis": "Testable", "description": "desc"}'
        ),
        jira_tool=FakeJiraTool(),
        jira_evaluator=FakeEvaluator(),
        confluence_tool=FakeConfluenceTool(
            result={"success": False, "error": "Space not configured"}
        ),
    )

    result = service.execute("create jira", [])

    assert result.success is True
    assert result.jira_result["success"] is True
    assert result.confluence_result == {
        "success": False,
        "error": "Space not configured",
    }
    assert "Confluence page creation failed" in result.response_text
