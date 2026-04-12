from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from src.agent.agent_graph import ChatbotAgent


def test_handle_general_chat_delegates_to_general_chat_service():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent.general_chat_service = MagicMock()
    agent.general_chat_service.handle.return_value = {
        "messages": [AIMessage(content="general reply")],
        "page_info": None,
    }

    state = {
        "messages": [],
        "user_input": "hello",
        "confluence_result": None,
    }

    result = agent._handle_general_chat(state)

    agent.general_chat_service.handle.assert_called_once()
    assert result["messages"][-1].content == "general reply"


def test_handle_rag_query_delegates_to_rag_query_service():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent.rag_query_service = MagicMock()
    agent.rag_query_service.handle.return_value = {
        "messages": [AIMessage(content="rag reply")],
        "rag_context": ["Chunk A"],
    }

    state = {
        "messages": [],
        "user_input": "what about PROJ-1",
        "rag_context": None,
    }

    result = agent._handle_rag_query(state)

    agent.rag_query_service.handle.assert_called_once()
    assert result["messages"][-1].content == "rag reply"
    assert result["rag_context"] == ["Chunk A"]


def test_handle_coze_agent_delegates_to_coze_agent_service():
    agent = ChatbotAgent.__new__(ChatbotAgent)
    agent.coze_agent_service = MagicMock()
    agent.coze_agent_service.handle.return_value = {
        "message": "Coze answer",
        "coze_result": {"success": True, "response": "Coze answer"},
    }

    state = {
        "messages": [],
        "user_input": "daily report",
        "coze_result": None,
    }

    result = agent._handle_coze_agent(state)

    agent.coze_agent_service.handle.assert_called_once()
    assert result["messages"][-1].content == "Coze answer"
    assert result["coze_result"]["success"] is True
