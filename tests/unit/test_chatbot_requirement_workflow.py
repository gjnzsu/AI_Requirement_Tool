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


def test_get_response_persists_requirement_sdlc_agent_state_with_persistent_memory():
    chatbot = Chatbot.__new__(Chatbot)
    chatbot.use_agent = True
    chatbot.agent = Mock()
    chatbot.agent.invoke.return_value = "preview ready"
    chatbot.agent.llm_callback = None
    chatbot.agent.export_requirement_sdlc_agent_state = Mock(
        return_value={"stage": "confirmation", "awaiting_confirmation": True}
    )
    chatbot.provider_name = "openai"
    chatbot.conversation_id = "conv-123"
    chatbot.use_persistent_memory = True
    chatbot.memory_manager = Mock()
    chatbot.memory_manager.get_conversation_messages.return_value = [
        {"role": "user", "content": "turn this into a requirement"}
    ]
    chatbot.memory_manager.add_message = Mock()
    chatbot.memory_manager.update_conversation_metadata = Mock()
    chatbot.conversation_history = []
    chatbot.max_history = 10
    chatbot.config = Mock()
    chatbot.config.get_llm_model = Mock(return_value="gpt-4")

    response = chatbot.get_response("approve")

    assert response == "preview ready"
    chatbot.memory_manager.add_message.assert_any_call("conv-123", "user", "approve")
    chatbot.memory_manager.add_message.assert_any_call("conv-123", "assistant", "preview ready")
    chatbot.memory_manager.update_conversation_metadata.assert_called_once_with(
        "conv-123",
        {
            "agent_mode": "auto",
            "requirement_sdlc_agent_state": {
                "stage": "confirmation",
                "awaiting_confirmation": True,
            },
        },
    )
