from unittest.mock import Mock

from src.chatbot import Chatbot
from src.webapp.runtime import AppRuntime


class FakeConfig:
    AUTH_DB_PATH = "auth.db"
    USE_PERSISTENT_MEMORY = True
    MEMORY_DB_PATH = "memory.db"
    MAX_CONTEXT_MESSAGES = 20
    LLM_PROVIDER = "openai"
    USE_MCP = True
    USE_RAG = True
    ENABLE_MCP_TOOLS = True

    @staticmethod
    def get_llm_model():
        return "gpt-4"


def test_execute_chat_request_restores_chatbot_state_when_memory_manager_exists():
    runtime = AppRuntime(config=FakeConfig)
    chatbot = Mock()
    original_provider_manager = Mock()
    original_provider_manager.primary = Mock(model="gpt-4")
    original_llm_provider = original_provider_manager.primary
    chatbot.provider_name = "openai"
    chatbot.provider_manager = original_provider_manager
    chatbot.llm_provider = original_llm_provider
    chatbot.conversation_id = "previous-conv"
    chatbot.conversation_history = [{"role": "user", "content": "old message"}]
    chatbot.last_usage = {"provider": "openai"}
    chatbot.agent = Mock()
    chatbot.agent.export_latest_requirement_workflow_progress = Mock(
        return_value=[{"step": "jira", "label": "Create Jira", "status": "completed"}]
    )
    chatbot.export_runtime_state = Mock(
        side_effect=[
            {"agent_mode": "auto", "requirement_sdlc_agent_state": {"stage": "idle"}},
            {"agent_mode": "requirement_sdlc_agent", "requirement_sdlc_agent_state": {"stage": "confirmation"}},
        ]
    )
    chatbot.load_runtime_state = Mock()
    chatbot.set_selected_agent_mode = Mock()
    def _switch_provider(value):
        chatbot.provider_name = value
        chatbot.provider_manager = None
        chatbot.llm_provider = Mock(model=f"{value}-model")

    chatbot.switch_provider = Mock(side_effect=_switch_provider)
    chatbot.set_conversation_id = Mock(side_effect=lambda value: setattr(chatbot, "conversation_id", value))
    chatbot.load_conversation = Mock(
        side_effect=lambda value: setattr(
            chatbot,
            "conversation_history",
            [{"role": "user", "content": f"loaded:{value}"}],
        )
    )

    def _get_response(message):
        chatbot.conversation_history.append({"role": "assistant", "content": "reply"})
        chatbot.last_usage = {"provider": "gemini"}
        return f"response:{message}"

    chatbot.get_response = Mock(side_effect=_get_response)
    runtime.memory_manager = Mock()

    result = runtime.execute_chat_request(
        message="hello",
        conversation_id="conv-123",
        model="gemini",
        agent_mode="requirement_sdlc_agent",
        chatbot=chatbot,
        memory_manager=runtime.memory_manager,
    )

    assert result.response == "response:hello"
    assert result.conversation_id == "conv-123"
    assert result.ui_actions == [
        {"label": "Approve", "value": "approve", "kind": "primary"},
        {"label": "Cancel", "value": "cancel", "kind": "secondary"},
    ]
    assert result.workflow_progress == [
        {"step": "jira", "label": "Create Jira", "status": "completed"},
    ]
    chatbot.switch_provider.assert_any_call("gemini")
    assert chatbot.switch_provider.call_count == 1
    chatbot.set_conversation_id.assert_called_once_with("conv-123")
    chatbot.load_conversation.assert_called_once_with("conv-123")
    chatbot.load_runtime_state.assert_called_once_with({"agent_mode": "auto", "requirement_sdlc_agent_state": {"stage": "idle"}})
    chatbot.set_selected_agent_mode.assert_called_once_with("requirement_sdlc_agent")
    runtime.memory_manager.update_conversation_metadata.assert_called_once_with(
        "conv-123",
        {"agent_mode": "requirement_sdlc_agent", "requirement_sdlc_agent_state": {"stage": "confirmation"}},
    )
    assert chatbot.conversation_id == "previous-conv"
    assert chatbot.provider_name == "openai"
    assert chatbot.provider_manager is original_provider_manager
    assert chatbot.llm_provider is original_llm_provider
    assert chatbot.conversation_history == [{"role": "user", "content": "old message"}]
    assert chatbot.last_usage == {"provider": "openai"}


def test_ensure_conversation_creates_in_memory_conversation_without_memory_manager():
    runtime = AppRuntime(config=FakeConfig)
    runtime.memory_manager = None

    conversation_id = runtime.ensure_conversation(
        conversation_id=None,
        title="New chat",
        generator=lambda: "conv-generated",
    )

    assert conversation_id == "conv-generated"
    assert runtime.conversations["conv-generated"]["title"] == "New chat"
    assert runtime.conversations["conv-generated"]["messages"] == []


def test_execute_chat_request_syncs_in_memory_conversation_history():
    runtime = AppRuntime(config=FakeConfig)
    runtime.memory_manager = None
    runtime.conversations["conv-123"] = {
        "messages": [{"role": "user", "content": "existing"}],
        "metadata": {"agent_mode": "auto", "requirement_sdlc_agent_state": {"stage": "analysis"}},
        "title": "Existing Chat",
        "created_at": "2026-04-10T00:00:00",
        "updated_at": "2026-04-10T00:00:00",
    }

    chatbot = Mock()
    chatbot.provider_name = "openai"
    chatbot.agent = Mock()
    chatbot.agent.export_latest_requirement_workflow_progress = Mock(return_value=None)
    chatbot.conversation_history = []
    chatbot.export_runtime_state = Mock(return_value={"agent_mode": "requirement_sdlc_agent", "requirement_sdlc_agent_state": {"stage": "preview"}})
    chatbot.set_selected_agent_mode = Mock()
    chatbot.switch_provider = Mock()
    chatbot.set_conversation_id = Mock()
    chatbot.load_conversation = Mock()

    def _get_response(message):
        chatbot.conversation_history.append({"role": "user", "content": message})
        chatbot.conversation_history.append({"role": "assistant", "content": "reply"})
        return "reply"

    chatbot.get_response = Mock(side_effect=_get_response)

    result = runtime.execute_chat_request(
        message="hello",
        conversation_id="conv-123",
        model="openai",
        agent_mode="requirement_sdlc_agent",
        chatbot=chatbot,
        memory_manager=None,
    )

    assert result.response == "reply"
    assert result.ui_actions is None
    assert result.workflow_progress is None
    assert runtime.conversations["conv-123"]["messages"] == [
        {"role": "user", "content": "existing"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "reply"},
    ]
    assert runtime.conversations["conv-123"]["metadata"] == {
        "agent_mode": "requirement_sdlc_agent",
        "requirement_sdlc_agent_state": {"stage": "preview"}
    }
    chatbot.set_selected_agent_mode.assert_called_once_with("requirement_sdlc_agent")
    chatbot.load_conversation.assert_not_called()


def test_execute_chat_request_restores_provider_state_with_in_memory_conversation():
    runtime = AppRuntime(config=FakeConfig)
    runtime.memory_manager = None
    runtime.conversations["conv-123"] = {
        "messages": [],
        "metadata": {},
        "title": "Existing Chat",
        "created_at": "2026-04-10T00:00:00",
        "updated_at": "2026-04-10T00:00:00",
    }

    chatbot = Mock()
    chatbot.provider_name = "openai"
    chatbot.provider_manager = None
    original_llm_provider = Mock(model="gpt-4")
    chatbot.llm_provider = original_llm_provider
    chatbot.conversation_history = []
    chatbot.export_runtime_state = Mock(return_value={})

    def _switch_provider(value):
        chatbot.provider_name = value
        chatbot.llm_provider.model = f"{value}-model"

    chatbot.switch_provider = Mock(side_effect=_switch_provider)
    chatbot.set_conversation_id = Mock()
    chatbot.load_conversation = Mock()
    chatbot.get_response = Mock(return_value="reply")

    result = runtime.execute_chat_request(
        message="hello",
        conversation_id="conv-123",
        model="gemini",
        chatbot=chatbot,
        memory_manager=None,
    )

    assert result.response == "reply"
    chatbot.switch_provider.assert_called_once_with("gemini")
    assert chatbot.provider_name == "openai"
    assert chatbot.llm_provider is original_llm_provider


def test_load_in_memory_conversation_restores_runtime_state_metadata():
    runtime = AppRuntime(config=FakeConfig)
    runtime.conversations["conv-123"] = {
        "messages": [{"role": "user", "content": "existing"}],
        "metadata": {"requirement_sdlc_agent_state": {"stage": "confirmation"}},
        "title": "Existing Chat",
        "created_at": "2026-04-10T00:00:00",
        "updated_at": "2026-04-10T00:00:00",
    }

    chatbot = Mock()
    chatbot.conversation_history = []
    chatbot.load_runtime_state = Mock()

    runtime._load_in_memory_conversation(chatbot, "conv-123")

    assert chatbot.conversation_history == [{"role": "user", "content": "existing"}]
    chatbot.load_runtime_state.assert_called_once_with(
        {"requirement_sdlc_agent_state": {"stage": "confirmation"}}
    )


def test_chatbot_load_conversation_restores_requirement_sdlc_agent_state_from_metadata():
    chatbot = Chatbot.__new__(Chatbot)
    chatbot.use_persistent_memory = True
    chatbot.memory_manager = Mock()
    chatbot.memory_manager.get_conversation.return_value = {
        "id": "conv-123",
        "title": "Skill chat",
        "summary": None,
        "metadata": {"agent_mode": "requirement_sdlc_agent", "requirement_sdlc_agent_state": {"stage": "confirmation", "awaiting_confirmation": True}},
        "messages": [{"role": "user", "content": "turn this into a requirement"}],
    }
    chatbot.agent = Mock()

    result = chatbot.load_conversation("conv-123")

    assert result is True
    assert chatbot.conversation_history == [
        {"role": "user", "content": "turn this into a requirement"}
    ]
    assert chatbot.selected_agent_mode == "requirement_sdlc_agent"
    chatbot.agent.load_requirement_sdlc_agent_state.assert_called_once_with(
        {"stage": "confirmation", "awaiting_confirmation": True}
    )


def test_chatbot_export_runtime_state_includes_requirement_sdlc_agent_state():
    chatbot = Chatbot.__new__(Chatbot)
    chatbot.selected_agent_mode = "requirement_sdlc_agent"
    chatbot.agent = Mock()
    chatbot.agent.export_requirement_sdlc_agent_state = Mock(
        return_value={"stage": "preview", "awaiting_confirmation": True}
    )

    assert chatbot.export_runtime_state() == {
        "agent_mode": "requirement_sdlc_agent",
        "requirement_sdlc_agent_state": {"stage": "preview", "awaiting_confirmation": True}
    }


def test_chatbot_load_runtime_state_restores_selected_agent_mode():
    chatbot = Chatbot.__new__(Chatbot)
    chatbot.selected_agent_mode = "auto"
    chatbot.agent = Mock()

    chatbot.load_runtime_state(
        {
            "agent_mode": "requirement_sdlc_agent",
            "requirement_sdlc_agent_state": {"stage": "analysis"},
        }
    )

    assert chatbot.selected_agent_mode == "requirement_sdlc_agent"
    chatbot.agent.set_selected_agent_mode.assert_called_once_with("requirement_sdlc_agent")
