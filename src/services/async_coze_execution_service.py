"""Async execution wrapper for Coze-backed agent turns."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from config.config import Config


class AsyncCozeExecutionService:
    """Execute a Coze turn and persist the assistant reply."""

    def __init__(
        self,
        *,
        coze_service: Any,
        memory_manager: Any,
        timestamp_provider: Optional[Callable[[], str]] = None,
    ) -> None:
        self.coze_service = coze_service
        self.memory_manager = memory_manager
        self.timestamp_provider = timestamp_provider or self._default_timestamp_provider

    @staticmethod
    def _default_timestamp_provider() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _extract_response_text(result: Any) -> str:
        if isinstance(result, dict):
            coze_result = result.get("coze_result")
            if isinstance(coze_result, dict) and coze_result.get("response") is not None:
                return str(coze_result.get("response", ""))
            if result.get("response") is not None:
                return str(result.get("response", ""))
            if result.get("message") is not None:
                return str(result.get("message", ""))
        if result is None:
            return ""
        return str(result)

    def execute(
        self,
        *,
        user_input: str,
        conversation_id: str,
        conversation_history: List[Dict[str, str]],
        agent_mode: str,
    ) -> Dict[str, Any]:
        """Run the Coze turn and return the completed async result payload."""
        coze_result = self.coze_service.handle(
            user_input=user_input,
            previous_result=None,
        )
        response_text = self._extract_response_text(coze_result)
        self._persist_user_message(
            conversation_id=conversation_id,
            user_input=user_input,
        )
        self._persist_assistant_message(
            conversation_id=conversation_id,
            response_text=response_text,
        )

        return {
            "response": response_text,
            "conversation_id": conversation_id,
            "agent_mode": agent_mode,
            "ui_actions": [],
            "workflow_progress": None,
            "timestamp": self.timestamp_provider(),
        }

    def _persist_user_message(self, *, conversation_id: str, user_input: str) -> None:
        if not self.memory_manager:
            return
        try:
            self.memory_manager.add_message(conversation_id, "user", user_input)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to persist user message for conversation {conversation_id}: {exc}"
            ) from exc

    def _persist_assistant_message(self, *, conversation_id: str, response_text: str) -> None:
        if not self.memory_manager:
            return
        try:
            self.memory_manager.add_message(conversation_id, "assistant", response_text)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to persist assistant message for conversation {conversation_id}: {exc}"
            ) from exc


def build_default_async_coze_execution_service() -> AsyncCozeExecutionService:
    """Build the worker-local Coze execution wrapper with concrete dependencies."""
    from src.services.coze_agent_service import CozeAgentService
    from src.services.coze_client import CozeClient
    from src.services.memory_manager import MemoryManager

    coze_client = CozeClient()
    coze_service = CozeAgentService(coze_client=coze_client)
    memory_manager = None
    if Config.USE_PERSISTENT_MEMORY:
        memory_manager = MemoryManager(
            db_path=Config.MEMORY_DB_PATH,
            max_context_messages=Config.MAX_CONTEXT_MESSAGES,
        )
    return AsyncCozeExecutionService(
        coze_service=coze_service,
        memory_manager=memory_manager,
    )
