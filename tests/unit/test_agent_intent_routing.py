"""Unit tests for pure keyword intent routing helpers."""

import pytest

from src.agent.intent_routing import detect_keyword_intent


@pytest.mark.unit
def test_detect_keyword_intent_prioritizes_confluence_tooling_over_rag_query():
    """Confluence tooling questions should stay in general chat, not route to RAG."""
    assert (
        detect_keyword_intent(
            "How does Confluence API integration work?",
            rag_service_available=True,
            jira_available=True,
            coze_enabled=True,
        )
        == "general_chat"
    )


@pytest.mark.unit
def test_detect_keyword_intent_routes_ai_news_to_coze_when_enabled():
    """AI news requests should route to Coze when that integration is enabled."""
    assert (
        detect_keyword_intent(
            "Please share AI daily news",
            rag_service_available=False,
            jira_available=False,
            coze_enabled=True,
        )
        == "coze_agent"
    )


@pytest.mark.unit
def test_detect_keyword_intent_routes_jira_key_lookup_to_rag_when_not_creation():
    """Jira key references should route to RAG lookup when not phrased as creation."""
    assert (
        detect_keyword_intent(
            "What was the acceptance criteria for AUTH-123?",
            rag_service_available=True,
            jira_available=True,
            coze_enabled=False,
        )
        == "rag_query"
    )
