"""Application service for Coze-backed agent execution."""

from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, Optional

from src.agent.coze_nodes import (
    build_coze_exception_message,
    build_coze_failure_message,
    build_coze_timeout_result,
    extract_previous_coze_conversation_id,
    resolve_coze_success_message,
)


class CozeAgentService:
    """Execute Coze requests and normalize user-facing messages."""

    def __init__(self, *, coze_client: Any, timeout_seconds: float = 300.0) -> None:
        self.coze_client = coze_client
        self.timeout_seconds = timeout_seconds

    def handle(
        self,
        *,
        user_input: str,
        previous_result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a Coze agent turn and return normalized output."""
        if not self.coze_client or not self.coze_client.is_configured():
            return {
                "message": (
                    "Coze agent is not properly configured. Please check your "
                    "COZE_API_TOKEN and COZE_BOT_ID settings."
                ),
                "coze_result": None,
            }

        try:
            conversation_id = extract_previous_coze_conversation_id(previous_result)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self.coze_client.execute_agent,
                    query=user_input,
                    user_id="default_user",
                    conversation_id=conversation_id,
                )
                try:
                    coze_result = future.result(timeout=self.timeout_seconds)
                except concurrent.futures.TimeoutError:
                    timeout_message, timeout_result = build_coze_timeout_result(
                        self.timeout_seconds
                    )
                    return {
                        "message": timeout_message,
                        "coze_result": timeout_result,
                    }

            if coze_result.get("success"):
                return {
                    "message": resolve_coze_success_message(coze_result),
                    "coze_result": coze_result,
                }

            return {
                "message": build_coze_failure_message(coze_result),
                "coze_result": coze_result,
            }
        except Exception as error:
            error_text = str(error)
            return {
                "message": build_coze_exception_message(error_text),
                "coze_result": {
                    "success": False,
                    "error": error_text,
                    "error_type": "exception",
                },
            }
