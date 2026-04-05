"""Unit tests for Confluence creation node helper functions."""

import pytest

from src.agent.confluence_nodes import (
    build_confluence_duplicate_result,
    build_confluence_error_message,
    build_confluence_page_link,
    build_confluence_rag_metadata,
    build_confluence_success_message,
    detect_confluence_error_code,
    normalize_mcp_confluence_dict_result,
    normalize_mcp_confluence_text_result,
)


@pytest.mark.unit
def test_build_confluence_page_link_handles_webui_paths_page_ids_and_explicit_links():
    """Link builder should normalize Confluence Cloud webui paths and fallback pageId URLs."""
    base_url = "https://example.atlassian.net/wiki"

    assert build_confluence_page_link(base_url, explicit_link="https://custom/link") == "https://custom/link"
    assert build_confluence_page_link(base_url, webui_path="/spaces/TEAM/pages/123/Plan") == (
        "https://example.atlassian.net/wiki/spaces/TEAM/pages/123/Plan"
    )
    assert build_confluence_page_link(base_url, page_id="123") == (
        "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123"
    )


@pytest.mark.unit
def test_normalize_mcp_confluence_text_result_parses_successful_text_payloads():
    """Text MCP responses with created/pageId/url data should normalize to a success payload."""
    result = normalize_mcp_confluence_text_result(
        "Page created successfully. pageId=123 https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123",
        page_title="Release Plan",
        confluence_url="https://example.atlassian.net/wiki",
    )

    assert result == {
        "success": True,
        "id": "123",
        "title": "Release Plan",
        "link": "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=123",
        "tool_used": "MCP Protocol",
    }


@pytest.mark.unit
def test_normalize_mcp_confluence_dict_result_supports_rovo_and_custom_shapes():
    """Dict normalization should accept both root-level ids and _links.webui paths."""
    rovo_result = normalize_mcp_confluence_dict_result(
        {
            "id": 456,
            "title": "Architecture",
            "_links": {"webui": "/spaces/ENG/pages/456/Architecture"},
        },
        page_title="Fallback Title",
        confluence_url="https://example.atlassian.net/wiki",
    )
    custom_result = normalize_mcp_confluence_dict_result(
        {
            "success": True,
            "pageId": "789",
            "title": "Runbook",
        },
        page_title="Fallback Title",
        confluence_url="https://example.atlassian.net/wiki",
    )

    assert rovo_result["success"] is True
    assert rovo_result["id"] == "456"
    assert rovo_result["link"] == "https://example.atlassian.net/wiki/spaces/ENG/pages/456/Architecture"
    assert custom_result["id"] == "789"
    assert custom_result["link"] == "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=789"


@pytest.mark.unit
def test_normalize_mcp_confluence_dict_result_raises_on_error_payloads():
    """Error dicts should surface a readable failure message for fallback handling."""
    with pytest.raises(ValueError, match="MCP tool error"):
        normalize_mcp_confluence_dict_result(
            {"success": False, "error": True, "error_type": "validation"},
            page_title="Release Plan",
            confluence_url="https://example.atlassian.net/wiki",
        )


@pytest.mark.unit
def test_build_confluence_messages_and_metadata_preserve_existing_copy():
    """Success, duplicate fallback, metadata, and error messages should stay behavior-compatible."""
    success_message = build_confluence_success_message(
        {"title": "Release Plan", "link": "https://wiki/page"},
        "Direct API",
    )
    duplicate_result = build_confluence_duplicate_result("Release Plan")
    metadata = build_confluence_rag_metadata(
        page_title="Release Plan",
        issue_key="PROJ-123",
        confluence_result={"id": "456", "link": "https://wiki/page"},
        created_at="2026-04-05T10:11:12",
    )
    timeout_message = build_confluence_error_message(
        error_code="TIMEOUT",
        tool_used="MCP Protocol",
        space_key="TEAM",
    )

    assert "Confluence Page Created (via Direct API)" in success_message
    assert duplicate_result == {
        "success": False,
        "error": 'Page with title "Release Plan" already exists. The MCP tool may have created it successfully, but we could not verify.',
        "tool_used": "Direct API (duplicate error)",
    }
    assert metadata == {
        "type": "confluence_page",
        "title": "Release Plan",
        "related_jira": "PROJ-123",
        "link": "https://wiki/page",
        "page_id": "456",
        "created_at": "2026-04-05T10:11:12",
    }
    assert "Confluence page creation failed (MCP Protocol)" in timeout_message


@pytest.mark.unit
def test_detect_confluence_error_code_maps_known_error_patterns():
    """Exception text detection should preserve the existing code mapping behavior."""
    assert detect_confluence_error_code("ConnectionResetError 10054") == "CONNECTION_RESET"
    assert detect_confluence_error_code("connection aborted by peer") == "CONNECTION_ABORTED"
    assert detect_confluence_error_code("request timeout") == "TIMEOUT"
    assert detect_confluence_error_code("401 unauthorized") == "AUTH_ERROR"
    assert detect_confluence_error_code("403 forbidden") == "PERMISSION_ERROR"
    assert detect_confluence_error_code("some other error") is None
