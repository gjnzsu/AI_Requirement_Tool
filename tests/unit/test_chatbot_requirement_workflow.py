from unittest.mock import Mock

from src.chatbot import Chatbot
from src.services.requirement_workflow_service import RequirementWorkflowResult


def test_handle_jira_creation_delegates_to_requirement_workflow_service():
    chatbot = Chatbot.__new__(Chatbot)
    chatbot.conversation_history = [
        {"role": "user", "content": "Need login audit trail"}
    ]
    chatbot.max_history = 10
    chatbot.provider_manager = None
    chatbot.llm_provider = Mock()
    chatbot.llm_provider.generate_response.return_value = (
        '{"summary": "Legacy path", "description": "desc", "priority": "Medium"}'
    )
    chatbot.jira_tool = Mock()
    chatbot.jira_tool.create_issue.return_value = {
        "success": True,
        "key": "PROJ-OLD",
        "link": "https://jira.example/browse/PROJ-OLD",
    }
    chatbot.jira_evaluator = None
    chatbot.confluence_tool = None
    chatbot.requirement_workflow_service = Mock()
    chatbot.requirement_workflow_service.execute.return_value = (
        RequirementWorkflowResult(
            success=True,
            response_text="delegated workflow response",
            jira_result={"success": True, "key": "PROJ-123"},
        )
    )

    response = chatbot._handle_jira_creation("create the jira")

    assert response == "delegated workflow response"
    chatbot.requirement_workflow_service.execute.assert_called_once_with(
        "create the jira",
        chatbot.conversation_history,
    )
