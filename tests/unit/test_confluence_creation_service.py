from types import SimpleNamespace
from unittest.mock import Mock

from src.services.confluence_creation_service import ConfluenceCreationService


def test_handle_generates_page_draft_and_delegates_to_confluence_port():
    llm_provider = Mock()
    llm_provider.invoke.return_value = SimpleNamespace(
        content='{"title": "Release Plan", "content": "<p>Deployment checklist</p>", "summary": "Deployment checklist"}'
    )
    confluence_page_port = Mock()
    confluence_page_port.create_page.return_value = {
        "success": True,
        "id": "456",
        "title": "Release Plan",
        "link": "https://wiki.example/pages/456",
        "tool_used": "Direct API",
    }

    service = ConfluenceCreationService(
        llm_provider=llm_provider,
        confluence_page_port=confluence_page_port,
    )

    result = service.handle(
        user_input="Create a Confluence page for the release plan and deployment checklist",
        messages=[],
        conversation_history=[],
    )

    confluence_page_port.create_page.assert_called_once_with(
        "Release Plan",
        "<p>Deployment checklist</p>",
    )
    assert result["confluence_result"]["success"] is True
    assert result["rag_metadata"]["page_id"] == "456"
    assert "Release Plan" in result["message"]


def test_handle_returns_error_when_confluence_port_is_missing():
    service = ConfluenceCreationService(
        llm_provider=Mock(),
        confluence_page_port=None,
    )

    result = service.handle(
        user_input="Create a Confluence page for the release plan",
        messages=[],
        conversation_history=[],
    )

    assert result["confluence_result"]["success"] is False
    assert "not configured" in result["message"].lower()
