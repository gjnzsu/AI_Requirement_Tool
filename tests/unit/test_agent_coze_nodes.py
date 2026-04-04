"""Unit tests for Coze agent node helper functions."""

import pytest

from src.agent.coze_nodes import (
    build_coze_failure_message,
    build_coze_timeout_result,
    extract_previous_coze_conversation_id,
    resolve_coze_success_message,
)


@pytest.mark.unit
def test_extract_previous_coze_conversation_id_reads_dict_state():
    """Previous Coze conversation id should be preserved when available."""
    assert (
        extract_previous_coze_conversation_id({"conversation_id": "conv-123"})
        == "conv-123"
    )
    assert extract_previous_coze_conversation_id(None) is None


@pytest.mark.unit
def test_build_coze_timeout_result_uses_timeout_minutes():
    """Timeout helper should return both user message and structured failure result."""
    message, result = build_coze_timeout_result(timeout_seconds=300)

    assert "5 minutes" in message
    assert result == {
        "success": False,
        "error": "Request timeout",
        "error_type": "timeout",
    }


@pytest.mark.unit
def test_resolve_coze_success_message_returns_response_or_empty_warning():
    """Successful Coze result should prefer response text and otherwise return fallback warning."""
    assert (
        resolve_coze_success_message({"success": True, "response": "Daily report ready"})
        == "Daily report ready"
    )
    assert "empty response" in resolve_coze_success_message({"success": True}).lower()


@pytest.mark.unit
def test_build_coze_failure_message_maps_http_and_network_errors():
    """Failure helper should map Coze error payloads to user-safe messages."""
    auth_message = build_coze_failure_message({
        "success": False,
        "error": "Authentication failed",
        "error_type": "http_error",
        "status_code": 401,
    })
    network_message = build_coze_failure_message({
        "success": False,
        "error": "Socket closed",
        "error_type": "network_error",
    })

    assert "Authentication failed" in auth_message
    assert "network connection" in network_message.lower()
