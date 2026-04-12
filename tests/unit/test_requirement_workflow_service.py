import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.services.requirement_workflow_service import (
    RequirementWorkflowResult,
    RequirementWorkflowService,
)
from langchain_core.messages import AIMessage, HumanMessage


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


class FakeJiraIssuePort:
    def __init__(self, result=None):
        self.result = result or SimpleNamespace(
            success=True,
            key="PROJ-123",
            link="https://jira.example/browse/PROJ-123",
            error=None,
            tool_used="Direct API",
            raw_result={
                "success": True,
                "key": "PROJ-123",
                "link": "https://jira.example/browse/PROJ-123",
            },
        )
        self.calls = []

    def create_issue(self, backlog_data):
        self.calls.append(backlog_data)
        return self.result


class FakeJiraEvaluationPort:
    def __init__(self, evaluation=None):
        self.evaluation = evaluation or {
            "overall_maturity_score": 90,
            "strengths": ["Clear business value"],
            "weaknesses": ["None"],
            "recommendations": ["Proceed to implementation"],
            "detailed_scores": {"clarity": 90},
        }
        self.calls = []

    def evaluate_issue(self, issue_key):
        self.calls.append(issue_key)
        return self.evaluation


class FakeConfluencePagePort:
    def __init__(self, result=None):
        self.result = result or SimpleNamespace(
            success=True,
            page_id="123",
            title="PROJ-123: Add login auditing",
            link="https://wiki.example/pages/123",
            error=None,
            tool_used="Direct API",
            raw_result={
                "success": True,
                "title": "PROJ-123: Add login auditing",
                "link": "https://wiki.example/pages/123",
            },
        )
        self.calls = []

    def create_page(self, page_title, confluence_content):
        self.calls.append((page_title, confluence_content))
        return self.result


class FakeRagService:
    def __init__(self, ingest_result="confluence_page:123", error=None):
        self.ingest_result = ingest_result
        self.error = error
        self.calls = []

    def ingest_text(self, content, metadata, document_id=None):
        self.calls.append(
            {
                "content": content,
                "metadata": metadata,
                "document_id": document_id,
            }
        )
        if self.error:
            raise self.error
        return self.ingest_result


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
    jira_issue_port = FakeJiraIssuePort()
    confluence_page_port = FakeConfluencePagePort()

    service = RequirementWorkflowService(
        llm_provider=llm_provider,
        jira_issue_port=jira_issue_port,
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=confluence_page_port,
    )

    result = service.execute(
        "create jira",
        [{"role": "user", "content": "Need login audit trail"}],
    )

    assert result.success is True
    assert result.jira_result["key"] == "PROJ-123"
    assert result.confluence_result["success"] is True
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "completed",
            "link": "https://jira.example/browse/PROJ-123",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "completed",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "completed",
            "link": "https://wiki.example/pages/123",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert jira_issue_port.calls[0]["summary"] == "Add login auditing"
    assert confluence_page_port.calls[0][0] == "PROJ-123: Add login auditing"
    assert "Successfully created Jira issue" in result.response_text
    assert "Maturity Evaluation Results" in result.response_text
    assert "Confluence Page Created" in result.response_text


def test_execute_backlog_data_marks_rag_completed_when_ingestion_succeeds():
    rag_service = FakeRagService(ingest_result="confluence_page:PROJ-123")
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=FakeConfluencePagePort(),
        rag_service=rag_service,
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "completed",
            "link": "https://jira.example/browse/PROJ-123",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "completed",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "completed",
            "link": "https://wiki.example/pages/123",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "completed",
            "detail": "confluence_page:PROJ-123",
        },
    ]
    assert rag_service.calls[0]["metadata"]["type"] == "confluence_page"
    assert rag_service.calls[0]["metadata"]["related_jira"] == "PROJ-123"
    assert rag_service.calls[0]["metadata"]["title"] == "PROJ-123: Add login auditing"


def test_execute_backlog_data_marks_rag_failed_when_ingestion_returns_none():
    rag_service = FakeRagService(ingest_result=None)
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=FakeConfluencePagePort(),
        rag_service=rag_service,
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert result.workflow_progress[-1] == {
        "step": "rag",
        "label": "Ingest to RAG",
        "status": "failed",
        "detail": "RAG ingestion did not return a document id.",
    }


def test_execute_returns_failure_when_backlog_json_is_invalid():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("not-json"),
        jira_issue_port=FakeJiraIssuePort(),
    )

    result = service.execute("create jira", [])

    assert result.success is False
    assert result.jira_result is None
    assert "Error processing Jira creation request" in result.response_text


def test_execute_backlog_data_marks_jira_failed_when_jira_tool_missing():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is False
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "failed",
            "detail": "Jira tool is not configured. Please check your Jira credentials.",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "skipped",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "skipped",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert (
        "I apologize, but the Jira tool is not configured correctly. "
        "Please check your Jira credentials."
    ) in result.response_text


def test_execute_returns_failure_when_jira_creation_fails():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider(
            '{"summary": "Bad issue", "description": "desc", "priority": "Medium"}'
        ),
        jira_issue_port=FakeJiraIssuePort(
            result=SimpleNamespace(
                success=False,
                key=None,
                link=None,
                error="Jira unavailable",
                tool_used="Direct API",
                raw_result={"success": False, "error": "Jira unavailable"},
            )
        ),
    )

    result = service.execute("create jira", [])

    assert result.success is False
    assert result.jira_result == {"success": False, "error": "Jira unavailable"}
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "failed",
            "detail": "Jira unavailable",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "skipped",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "skipped",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert "Failed to create Jira issue: Jira unavailable" in result.response_text


def test_execute_backlog_data_catches_jira_creation_exception():
    class ExplodingJiraIssuePort:
        def create_issue(self, backlog_data):
            raise RuntimeError("jira boom")

    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=ExplodingJiraIssuePort(),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is False
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "failed",
            "detail": "jira boom",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "skipped",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "skipped",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert result.jira_result is None
    assert "Failed to create Jira issue: jira boom" in result.response_text


def test_execute_backlog_data_treats_missing_jira_fields_as_failure():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(
            result=SimpleNamespace(
                success=True,
                key=None,
                link=None,
                error=None,
                tool_used="Direct API",
                raw_result={"success": True},
            )
        ),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is False
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "failed",
            "detail": "Jira issue creation succeeded but returned no issue key or link.",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "skipped",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "skipped",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert result.jira_result == {"success": True}
    assert (
        "Failed to create Jira issue: Jira issue creation succeeded but returned no issue key or link."
        in result.response_text
    )


def test_execute_backlog_data_catches_confluence_creation_exception_after_successful_evaluation():
    class ExplodingConfluencePagePort:
        def create_page(self, page_title, confluence_content):
            raise RuntimeError("confluence boom")

    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=ExplodingConfluencePagePort(),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "completed",
            "link": "https://jira.example/browse/PROJ-123",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "completed",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "failed",
            "detail": "confluence boom",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert result.evaluation_result["overall_maturity_score"] == 90
    assert "Maturity Evaluation Results" in result.response_text
    assert "Maturity evaluation failed" not in result.response_text


def test_execute_preserves_jira_success_when_confluence_creation_fails():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider(
            '{"summary": "Add reporting", "business_value": "Visibility", '
            '"acceptance_criteria": ["Reports exist"], "priority": "Medium", '
            '"invest_analysis": "Testable", "description": "desc"}'
        ),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=FakeConfluencePagePort(
            result=SimpleNamespace(
                success=False,
                page_id=None,
                title=None,
                link=None,
                error="Space not configured",
                tool_used="Direct API",
                raw_result={"success": False, "error": "Space not configured"},
            )
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


def test_execute_backlog_data_formats_confluence_success_without_title():
    class UntitledConfluencePagePort:
        def __init__(self):
            self.calls = []

        def create_page(self, page_title, confluence_content):
            self.calls.append((page_title, confluence_content))
            return SimpleNamespace(
                success=True,
                page_id="123",
                link="https://wiki.example/pages/123",
                error=None,
                tool_used="Direct API",
                raw_result={
                    "success": True,
                    "link": "https://wiki.example/pages/123",
                },
            )

    confluence_page_port = UntitledConfluencePagePort()
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=confluence_page_port,
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert result.confluence_result == {
        "success": True,
        "id": "123",
        "link": "https://wiki.example/pages/123",
    }
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "completed",
            "link": "https://jira.example/browse/PROJ-123",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "completed",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "completed",
            "link": "https://wiki.example/pages/123",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert "Confluence Page Created" in result.response_text


def test_execute_backlog_data_treats_partial_evaluation_payload_as_failure():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(
            evaluation={
                "strengths": ["Clear business value"],
                "weaknesses": ["None"],
                "recommendations": ["Proceed to implementation"],
            }
        ),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert result.workflow_progress == [
        {
            "step": "jira",
            "label": "Create Jira",
            "status": "completed",
            "link": "https://jira.example/browse/PROJ-123",
        },
        {
            "step": "evaluation",
            "label": "Evaluate Requirement",
            "status": "failed",
            "detail": "Jira evaluation returned an incomplete result.",
        },
        {
            "step": "confluence",
            "label": "Create Confluence Page",
            "status": "skipped",
        },
        {
            "step": "rag",
            "label": "Ingest to RAG",
            "status": "skipped",
        },
    ]
    assert result.evaluation_result == {
        "strengths": ["Clear business value"],
        "weaknesses": ["None"],
        "recommendations": ["Proceed to implementation"],
    }
    assert "Could not evaluate maturity: Jira evaluation returned an incomplete result." in result.response_text


def test_execute_backlog_data_runs_lifecycle_without_regenerating_backlog():
    llm_provider = FakeLLMProvider("unused")
    jira_issue_port = FakeJiraIssuePort()
    confluence_page_port = FakeConfluencePagePort()

    service = RequirementWorkflowService(
        llm_provider=llm_provider,
        jira_issue_port=jira_issue_port,
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=confluence_page_port,
    )

    backlog_data = {
        "summary": "Add login auditing",
        "business_value": "Improves security traceability",
        "acceptance_criteria": ["Every login is recorded"],
        "priority": "High",
        "invest_analysis": "Small and testable",
        "description": "Business Value: Improves security traceability",
    }

    result = service.execute_backlog_data(backlog_data)

    assert result.success is True
    assert result.jira_result["key"] == "PROJ-123"
    assert jira_issue_port.calls[0] == backlog_data
    assert llm_provider.calls == []
    assert "Successfully created Jira issue" in result.response_text


def test_execute_preserves_legacy_generate_response_path_when_invoke_exists():
    llm_provider = MagicMock()
    llm_provider.generate_response.return_value = '{"summary": "Legacy issue", "description": "desc", "priority": "Medium"}'
    llm_provider.invoke.return_value = SimpleNamespace(
        content='{"summary": "Wrong path", "description": "desc", "priority": "Medium"}'
    )

    service = RequirementWorkflowService(
        llm_provider=llm_provider,
        jira_issue_port=FakeJiraIssuePort(),
    )

    result = service.execute("create jira", [])

    assert result.success is True
    assert result.backlog_data["summary"] == "Legacy issue"
    llm_provider.generate_response.assert_called_once()
    llm_provider.invoke.assert_not_called()


def test_execute_delegates_generated_backlog_to_execute_backlog_data():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider(
            '{"summary": "Generated issue", "description": "desc", "priority": "Medium"}'
        ),
        jira_issue_port=FakeJiraIssuePort(),
    )

    with patch.object(
        service,
        "execute_backlog_data",
        return_value=RequirementWorkflowResult(success=True, response_text="ok"),
    ) as execute_backlog_data:
        result = service.execute("create jira", [])

    assert result.response_text == "ok"
    execute_backlog_data.assert_called_once()
    assert execute_backlog_data.call_args.args[0] == {
        "summary": "Generated issue",
        "description": "desc",
        "priority": "Medium",
    }


class FakeAgentLLM:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=self.content)


def test_generate_backlog_data_for_agent_context_uses_agent_prompt_shape():
    service = RequirementWorkflowService(
        llm_provider=FakeAgentLLM(
            '{"summary": "Agent issue", "description": "desc", "priority": "Medium"}'
        ),
        jira_issue_port=FakeJiraIssuePort(),
    )

    backlog_data = service.generate_backlog_data_for_agent(
        user_input="please create a jira ticket",
        messages=[HumanMessage(content="Need audit trail"), AIMessage(content="Tell me more")],
        conversation_history=[{"role": "user", "content": "Track login events"}],
    )

    assert backlog_data["summary"] == "Agent issue"


def test_create_jira_issue_returns_normalized_result_payload():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("{}"),
        jira_issue_port=FakeJiraIssuePort(),
    )

    jira_result = service.create_jira_issue({"summary": "Agent issue"})

    assert jira_result["success"] is True
    assert jira_result["key"] == "PROJ-123"
    assert jira_result["link"] == "https://jira.example/browse/PROJ-123"


def test_generate_backlog_data_for_agent_prefers_invoke_for_langchain_style_mocks():
    llm_provider = MagicMock()
    llm_provider.invoke.return_value = SimpleNamespace(
        content='{"summary": "Mock issue", "description": "desc", "priority": "Medium"}'
    )

    service = RequirementWorkflowService(
        llm_provider=llm_provider,
        jira_issue_port=FakeJiraIssuePort(),
    )

    backlog_data = service.generate_backlog_data_for_agent(
        user_input="create a jira ticket",
        messages=[HumanMessage(content="Need an issue")],
        conversation_history=[],
    )

    assert backlog_data["summary"] == "Mock issue"
    llm_provider.invoke.assert_called_once()
    llm_provider.generate_response.assert_not_called()


def test_create_confluence_page_tolerates_missing_evaluation_scores():
    confluence_page_port = FakeConfluencePagePort()
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("{}"),
        confluence_page_port=confluence_page_port,
    )

    result = service.create_confluence_page(
        issue_key="PROJ-123",
        backlog_data={
            "summary": "Add login auditing",
            "business_value": "Improve traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Testable",
        },
        evaluation_result={},
        jira_link="https://jira.example/browse/PROJ-123",
    )

    assert result["success"] is True
    assert confluence_page_port.calls
    _, confluence_content = confluence_page_port.calls[0]
    assert "Maturity Evaluation" not in confluence_content
