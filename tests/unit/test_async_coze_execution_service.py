from __future__ import annotations

from inspect import signature
from unittest.mock import Mock

import pytest

from src.async_jobs.tasks import process_coze_job
import src.services.async_coze_execution_service as async_coze_module
from src.services.async_coze_execution_service import (
    AsyncCozeExecutionService,
    build_default_async_coze_execution_service,
)


class _FakeMemoryManager:
    def __init__(self) -> None:
        self.messages_by_conversation: dict[str, list[dict[str, str]]] = {}

    def add_message(self, conversation_id: str, role: str, content: str):
        self.messages_by_conversation.setdefault(conversation_id, []).append(
            {"role": role, "content": content}
        )


@pytest.mark.unit
def test_execute_writes_assistant_message_into_conversation_storage():
    coze_service = Mock()
    coze_service.handle.return_value = {
        "message": "Coze completed",
        "coze_result": {"success": True, "response": "Final assistant reply"},
    }
    memory_manager = _FakeMemoryManager()
    service = AsyncCozeExecutionService(
        coze_service=coze_service,
        memory_manager=memory_manager,
        timestamp_provider=lambda: "2026-04-18T10:11:12",
    )

    result = service.execute(
        user_input="Summarize today's work",
        conversation_id="conv-123",
        conversation_history=[{"role": "user", "content": "Hi"}],
        agent_mode="coze_agent",
    )

    coze_service.handle.assert_called_once_with(
        user_input="Summarize today's work",
        previous_result={
            "conversation_id": "conv-123",
            "conversation_history": [{"role": "user", "content": "Hi"}],
            "agent_mode": "coze_agent",
        },
    )
    assert memory_manager.messages_by_conversation == {
        "conv-123": [
            {"role": "user", "content": "Summarize today's work"},
            {"role": "assistant", "content": "Final assistant reply"},
        ]
    }
    assert result == {
        "response": "Final assistant reply",
        "conversation_id": "conv-123",
        "agent_mode": "coze_agent",
        "ui_actions": [],
        "workflow_progress": None,
        "timestamp": "2026-04-18T10:11:12",
    }


@pytest.mark.unit
def test_process_coze_job_builds_execution_service_internally(monkeypatch):
    execution_service = Mock()
    execution_service.execute.return_value = {
        "response": "done",
        "conversation_id": "conv-123",
        "agent_mode": "coze_agent",
        "ui_actions": [],
        "workflow_progress": None,
        "timestamp": "2026-04-18T10:11:12",
    }
    build_execution_service = Mock(return_value=execution_service)
    monkeypatch.setattr(
        "src.services.async_coze_execution_service.build_default_async_coze_execution_service",
        build_execution_service,
    )

    result = process_coze_job(
        user_input="Hello",
        conversation_id="conv-123",
        conversation_history=[],
        agent_mode="coze_agent",
    )

    build_execution_service.assert_called_once_with()
    execution_service.execute.assert_called_once_with(
        user_input="Hello",
        conversation_id="conv-123",
        conversation_history=[],
        agent_mode="coze_agent",
    )
    assert result == execution_service.execute.return_value


@pytest.mark.unit
def test_process_coze_job_payload_shape_excludes_execution_service():
    assert "execution_service" not in signature(process_coze_job).parameters


@pytest.mark.unit
def test_build_default_async_coze_execution_service_uses_configured_persistent_memory(
    monkeypatch,
):
    created_memory_managers = []

    class _FakeMemoryManager:
        def __init__(self, *, db_path=None, max_context_messages=None):
            created_memory_managers.append(
                {"db_path": db_path, "max_context_messages": max_context_messages}
            )

    class _FakeCozeClient:
        pass

    class _FakeCozeAgentService:
        def __init__(self, *, coze_client):
            self.coze_client = coze_client

    monkeypatch.setattr(async_coze_module.Config, "USE_PERSISTENT_MEMORY", True, raising=False)
    monkeypatch.setattr(async_coze_module.Config, "MEMORY_DB_PATH", "memory.db", raising=False)
    monkeypatch.setattr(async_coze_module.Config, "MAX_CONTEXT_MESSAGES", 42, raising=False)
    monkeypatch.setattr(
        "src.services.coze_client.CozeClient",
        _FakeCozeClient,
    )
    monkeypatch.setattr(
        "src.services.coze_agent_service.CozeAgentService",
        _FakeCozeAgentService,
    )
    monkeypatch.setattr(
        "src.services.memory_manager.MemoryManager",
        _FakeMemoryManager,
    )

    service = build_default_async_coze_execution_service()

    assert created_memory_managers == [
        {"db_path": "memory.db", "max_context_messages": 42}
    ]
    assert service.memory_manager is not None
    assert isinstance(service.coze_service, _FakeCozeAgentService)


@pytest.mark.unit
def test_build_default_async_coze_execution_service_skips_persistent_memory_when_disabled(
    monkeypatch,
):
    memory_manager_ctor = Mock()

    class _FakeCozeClient:
        pass

    class _FakeCozeAgentService:
        def __init__(self, *, coze_client):
            self.coze_client = coze_client

    monkeypatch.setattr(async_coze_module.Config, "USE_PERSISTENT_MEMORY", False, raising=False)
    monkeypatch.setattr(
        "src.services.coze_client.CozeClient",
        _FakeCozeClient,
    )
    monkeypatch.setattr(
        "src.services.coze_agent_service.CozeAgentService",
        _FakeCozeAgentService,
    )
    monkeypatch.setattr(
        "src.services.memory_manager.MemoryManager",
        memory_manager_ctor,
    )

    service = build_default_async_coze_execution_service()

    memory_manager_ctor.assert_not_called()
    assert service.memory_manager is None


@pytest.mark.unit
def test_execute_raises_controlled_error_when_persisting_assistant_message_fails():
    class _FailingMemoryManager:
        def __init__(self) -> None:
            self.messages_by_conversation: dict[str, list[dict[str, str]]] = {}

        def add_message(self, conversation_id: str, role: str, content: str):
            if role == "user":
                self.messages_by_conversation.setdefault(conversation_id, []).append(
                    {"role": role, "content": content}
                )
                return None
            raise RuntimeError("sqlite write failed")

    coze_service = Mock()
    coze_service.handle.return_value = {
        "message": "Coze completed",
        "coze_result": {"success": True, "response": "Final assistant reply"},
    }
    service = AsyncCozeExecutionService(
        coze_service=coze_service,
        memory_manager=_FailingMemoryManager(),
        timestamp_provider=lambda: "2026-04-18T10:11:12",
    )

    with pytest.raises(
        RuntimeError,
        match="Failed to persist assistant message for conversation conv-123",
    ):
        service.execute(
            user_input="Summarize today's work",
            conversation_id="conv-123",
            conversation_history=[],
            agent_mode="coze_agent",
        )

    assert service.memory_manager.messages_by_conversation == {
        "conv-123": [{"role": "user", "content": "Summarize today's work"}]
    }
