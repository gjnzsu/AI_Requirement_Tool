"""Unit tests for general-chat node helper functions."""

from types import SimpleNamespace

import pytest

from src.agent.general_chat_nodes import (
    build_confluence_page_context,
    build_general_chat_error_message,
    parse_confluence_page_reference,
)


@pytest.mark.unit
def test_parse_confluence_page_reference_reads_issue_page_id_and_title():
    """Helper should parse supported Confluence reference forms from user input."""
    assert parse_confluence_page_reference(
        "What is the confluence page for AUTH-123?",
        {"success": True, "id": "456", "title": "Auth Design"},
    ) == ("456", "Auth Design")
    assert parse_confluence_page_reference("Show confluence page id 789", None) == ("789", None)
    assert parse_confluence_page_reference("Show confluence page titled Release Plan", None) == (
        None,
        "Release Plan",
    )


@pytest.mark.unit
def test_build_confluence_page_context_includes_title_link_and_content_preview():
    """Context formatter should append MCP page metadata and a 500-char content preview."""
    page_context = build_confluence_page_context({
        "title": "Auth Page",
        "link": "https://wiki/page",
        "content": "A" * 520,
    })

    assert "Title: Auth Page" in page_context
    assert "Link: https://wiki/page" in page_context
    assert f"Content Preview: {'A' * 500}..." in page_context


@pytest.mark.unit
def test_build_general_chat_error_message_maps_timeout_auth_and_rate_limit():
    """Error helper should map provider exceptions to the existing user-facing messages."""
    timeout_message, timeout_code = build_general_chat_error_message(
        TimeoutError("request timeout"),
        provider_name="openai",
    )
    auth_error = SimpleNamespace(status_code=401)
    rate_limit_error = SimpleNamespace(status_code=429)
    auth_message, auth_code = build_general_chat_error_message(auth_error, provider_name="openai")
    rate_limit_message, rate_limit_code = build_general_chat_error_message(
        rate_limit_error,
        provider_name="openai",
    )

    assert "trouble connecting" in timeout_message.lower()
    assert timeout_code is None
    assert "authentication issue" in auth_message.lower()
    assert auth_code == 401
    assert "rate limit exceeded" in rate_limit_message.lower()
    assert rate_limit_code == 429
