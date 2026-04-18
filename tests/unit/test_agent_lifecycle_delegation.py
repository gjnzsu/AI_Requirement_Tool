from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from src.agent.agent_graph import ChatbotAgent


def make_agent_stub():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent._refresh_application_services = lambda: None
    agent._refresh_flow_services = lambda: None
    agent._ingest_to_rag = Mock()
    agent._simplify_for_rag = Mock(return_value="compact confluence text")
    agent.requirement_workflow_service = Mock()
    agent.confluence_creation_service = Mock()
    agent.jira_issue_port = object()
    agent.jira_evaluation_port = object()
    agent.confluence_page_port = object()
    agent.llm = Mock()
    return agent


def test_handle_jira_creation_delegates_generation_and_jira_creation_to_workflow_service():
    agent = make_agent_stub()
    agent.llm.invoke.side_effect = AssertionError("agent handler should delegate backlog generation")
    agent.requirement_workflow_service.generate_backlog_data_for_agent.return_value = {
        "summary": "Delegated issue",
        "description": "desc",
        "priority": "High",
    }
    agent.requirement_workflow_service.create_jira_issue.return_value = {
        "success": True,
        "key": "PROJ-123",
        "link": "https://jira.example/browse/PROJ-123",
        "tool_used": "Direct API",
    }

    state = {
        "messages": [],
        "user_input": "please create a jira ticket",
        "intent": "jira_creation",
        "jira_result": None,
        "evaluation_result": None,
        "confluence_result": None,
        "rag_context": None,
        "conversation_history": [],
        "next_action": None,
    }

    result = agent._handle_jira_creation(state)

    agent.requirement_workflow_service.generate_backlog_data_for_agent.assert_called_once()
    agent.requirement_workflow_service.create_jira_issue.assert_called_once()
    assert result["jira_result"]["key"] == "PROJ-123"


def test_handle_evaluation_delegates_to_workflow_service():
    agent = make_agent_stub()
    agent.requirement_workflow_service.evaluate_issue.return_value = {
        "overall_maturity_score": 88,
        "strengths": ["Clear AC"],
        "recommendations": ["Proceed"],
    }
    agent.requirement_workflow_service.format_evaluation_result.return_value = "formatted evaluation"

    state = {
        "messages": [],
        "user_input": "please create a jira ticket",
        "intent": "jira_creation",
        "jira_result": {"success": True, "key": "PROJ-123"},
        "evaluation_result": None,
        "confluence_result": None,
        "rag_context": None,
        "conversation_history": [],
        "next_action": None,
    }

    result = agent._handle_evaluation(state)

    agent.requirement_workflow_service.evaluate_issue.assert_called_once_with("PROJ-123")
    agent.requirement_workflow_service.format_evaluation_result.assert_called_once()
    assert result["evaluation_result"]["overall_maturity_score"] == 88
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == "formatted evaluation"


def test_handle_confluence_creation_delegates_page_creation_to_workflow_service():
    agent = make_agent_stub()
    agent.requirement_workflow_service.create_confluence_page.return_value = {
        "success": True,
        "id": "123",
        "title": "PROJ-123: Delegated issue",
        "link": "https://wiki.example/pages/123",
        "tool_used": "Direct API",
    }

    state = {
        "messages": [],
        "user_input": "please create a jira ticket",
        "intent": "jira_creation",
        "jira_result": {
            "success": True,
            "key": "PROJ-123",
            "link": "https://jira.example/browse/PROJ-123",
            "backlog_data": {"summary": "Delegated issue"},
        },
        "evaluation_result": {"overall_maturity_score": 88},
        "confluence_result": None,
        "rag_context": None,
        "conversation_history": [],
        "next_action": None,
    }

    result = agent._handle_confluence_creation(state)

    agent.requirement_workflow_service.create_confluence_page.assert_called_once_with(
        issue_key="PROJ-123",
        backlog_data={"summary": "Delegated issue"},
        evaluation_result={"overall_maturity_score": 88},
        jira_link="https://jira.example/browse/PROJ-123",
    )
    assert result["confluence_result"]["success"] is True


def test_handle_confluence_creation_delegates_direct_freeform_requests_to_standalone_service():
    agent = make_agent_stub()
    agent.confluence_creation_service.handle.return_value = {
        "message": "Created Confluence page: Release Plan",
        "confluence_result": {
            "success": True,
            "id": "456",
            "title": "Release Plan",
            "link": "https://wiki.example/pages/456",
            "tool_used": "Direct API",
        },
        "rag_document": "Release Plan\nSummary of rollout steps",
        "rag_metadata": {
            "type": "confluence_page",
            "title": "Release Plan",
            "link": "https://wiki.example/pages/456",
            "page_id": "456",
        },
    }

    state = {
        "messages": [],
        "user_input": "Create a Confluence page for the release plan and deployment checklist",
        "intent": "confluence_creation",
        "jira_result": None,
        "evaluation_result": None,
        "confluence_result": None,
        "rag_context": None,
        "conversation_history": [],
        "next_action": None,
    }

    result = agent._handle_confluence_creation(state)

    agent.confluence_creation_service.handle.assert_called_once_with(
        user_input="Create a Confluence page for the release plan and deployment checklist",
        messages=[],
        conversation_history=[],
    )
    assert result["confluence_result"]["success"] is True
    agent._ingest_to_rag.assert_called_once()
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == "Created Confluence page: Release Plan"
