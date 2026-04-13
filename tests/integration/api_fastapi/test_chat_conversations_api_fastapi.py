"""Parity tests for FastAPI chat, model, and conversation endpoints."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.fastapi_app.app import create_fastapi_app


@pytest.fixture(scope="function")
def fastapi_runtime(monkeypatch):
    runtime = SimpleNamespace(
        auth_service=None,
        user_service=None,
        memory_manager=None,
        conversations={},
    )

    def fake_create_app_runtime(*args, **kwargs):
        return runtime

    monkeypatch.setattr("src.fastapi_app.app.create_app_runtime", fake_create_app_runtime)
    monkeypatch.setenv("BYPASS_AUTH", "1")

    app = create_fastapi_app()
    with TestClient(app) as client:
        yield client, runtime


def test_chat_success_returns_contract_payload(fastapi_runtime):
    client, runtime = fastapi_runtime

    runtime.ensure_conversation = Mock(return_value="conv-123")
    runtime.get_chatbot = Mock(return_value=Mock(provider_name="openai"))
    runtime.execute_chat_request = Mock(
        return_value=SimpleNamespace(
            response="Mocked chatbot response",
            conversation_id="conv-123",
            usage_info=None,
            ui_actions=None,
            workflow_progress=None,
        )
    )

    response = client.post("/api/chat", json={"message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Mocked chatbot response"
    assert data["conversation_id"] == "conv-123"
    assert data["agent_mode"] == "auto"
    assert "timestamp" in data


def test_chat_validates_model_and_message(fastapi_runtime):
    client, runtime = fastapi_runtime
    runtime.ensure_conversation = Mock(return_value="conv-123")
    runtime.get_chatbot = Mock(return_value=Mock(provider_name="openai"))
    runtime.execute_chat_request = Mock(return_value=SimpleNamespace(response="ok", ui_actions=None, workflow_progress=None))

    bad_model_response = client.post("/api/chat", json={"message": "Hello", "model": "invalid"})
    missing_message_response = client.post("/api/chat", json={})

    assert bad_model_response.status_code == 400
    assert "Invalid model" in bad_model_response.json()["error"]
    assert missing_message_response.status_code == 400
    assert missing_message_response.json() == {"error": "Message is required"}


def test_current_model_returns_provider_and_available_models(fastapi_runtime):
    client, runtime = fastapi_runtime
    runtime.get_chatbot = Mock(return_value=SimpleNamespace(provider_name="gemini"))

    response = client.get("/api/current-model")

    assert response.status_code == 200
    assert response.json() == {
        "model": "gemini",
        "available_models": ["openai", "gemini", "deepseek"],
    }


def test_list_conversations_uses_memory_manager_shape(fastapi_runtime):
    client, runtime = fastapi_runtime
    runtime.memory_manager = Mock()
    runtime.memory_manager.list_conversations.return_value = [
        {
            "id": "conv-1",
            "title": "First",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:01:00",
            "message_count": 2,
        }
    ]

    response = client.get("/api/conversations")

    assert response.status_code == 200
    assert response.json() == {
        "conversations": [
            {
                "id": "conv-1",
                "title": "First",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:01:00",
                "message_count": 2,
            }
        ]
    }


def test_conversation_crud_and_search_with_in_memory_store(fastapi_runtime, monkeypatch):
    client, runtime = fastapi_runtime
    runtime.conversations = {
        "conv-a": {
            "messages": [{"role": "user", "content": "hello python"}],
            "title": "Python chat",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:01",
        }
    }

    get_response = client.get("/api/conversations/conv-a")
    update_response = client.put("/api/conversations/conv-a/title", json={"title": "Updated"})
    search_response = client.get("/api/search?q=python&limit=5")

    monkeypatch.setattr("src.fastapi_app.routes.conversations.generate_conversation_id", lambda: "conv-new")
    new_chat_response = client.post("/api/new-chat")
    delete_response = client.delete("/api/conversations/conv-new")

    assert get_response.status_code == 200
    assert get_response.json()["conversation"]["title"] == "Python chat"
    assert update_response.status_code == 200
    assert update_response.json() == {"success": True, "title": "Updated"}
    assert search_response.status_code == 200
    assert len(search_response.json()["conversations"]) == 1
    assert new_chat_response.status_code == 200
    assert new_chat_response.json() == {"conversation_id": "conv-new", "success": True}
    assert delete_response.status_code == 200
    assert delete_response.json() == {"success": True}


def test_search_validation_errors_match_flask_messages(fastapi_runtime):
    client, _ = fastapi_runtime

    missing_query = client.get("/api/search")
    invalid_limit = client.get("/api/search?q=test&limit=abc")

    assert missing_query.status_code == 400
    assert missing_query.json() == {"error": "Search query is required"}
    assert invalid_limit.status_code == 400
    assert invalid_limit.json() == {"error": "Invalid limit: abc. Must be an integer."}
