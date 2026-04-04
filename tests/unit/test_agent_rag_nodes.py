"""Unit tests for RAG node helper functions."""

import pytest

from src.agent.rag_nodes import (
    build_rag_error_message,
    build_rag_prompt,
    extract_chunk_contents,
    extract_jira_key,
    load_direct_jira_context,
)


class FakeVectorStore:
    """Minimal fake vector store for direct Jira-key context lookup tests."""

    def __init__(self, documents):
        self._documents = documents

    def get_document(self, document_id):
        return self._documents.get(document_id)

    def list_documents(self):
        return [{"id": document_id} for document_id in self._documents]


@pytest.mark.unit
def test_extract_jira_key_returns_uppercase_issue_key():
    """Helper should extract Jira issue keys without lowercasing the raw value."""
    assert extract_jira_key("What about AUTH-123?") == "AUTH-123"
    assert extract_jira_key("No key here") is None


@pytest.mark.unit
def test_load_direct_jira_context_collects_issue_and_related_confluence_docs():
    """Direct lookup should combine Jira issue content and matching Confluence content."""
    vector_store = FakeVectorStore({
        "jira_issue:AUTH-123": {"content": "Jira acceptance criteria"},
        "confluence_page:AUTH-123-design": {"content": "Confluence design notes"},
        "confluence_page:OTHER-9": {"content": "Unrelated"},
    })

    context = load_direct_jira_context(vector_store, "AUTH-123")

    assert "Jira acceptance criteria" in context
    assert "Confluence design notes" in context
    assert "Unrelated" not in context


@pytest.mark.unit
def test_build_rag_prompt_wraps_context_and_user_question():
    """Prompt helper should preserve context and user question in one final prompt string."""
    prompt = build_rag_prompt("Context block", "What is AUTH-123?")

    assert "Context block" in prompt
    assert "User Question: What is AUTH-123?" in prompt


@pytest.mark.unit
def test_extract_chunk_contents_returns_content_list():
    """Chunk helper should extract content values with empty-string fallback."""
    assert extract_chunk_contents([{"content": "A"}, {}, {"content": "B"}]) == ["A", "", "B"]


@pytest.mark.unit
def test_build_rag_error_message_maps_timeout_and_auth_errors():
    """Error helper should convert raw exception text to user-safe responses."""
    assert "timed out" in build_rag_error_message("timeout from provider").lower()
    assert "authentication" in build_rag_error_message("401 unauthorized").lower()
