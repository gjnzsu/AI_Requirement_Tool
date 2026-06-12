from unittest.mock import Mock

import pytest
import requests

from src.adapters.rag import EmbeddedRagAdapter, ExternalRagAdapter


class FakeVectorStore:
    def get_document(self, document_id):
        if document_id == "jira_issue:PROJ-123":
            return {"content": "Jira content"}
        if document_id == "confluence_page:PROJ-123-design":
            return {"content": "Confluence content"}
        return None

    def list_documents(self):
        return [{"id": "confluence_page:PROJ-123-design"}]


class FakeEmbeddedService:
    def __init__(self):
        self.vector_store = FakeVectorStore()
        self.ingest_calls = []

    def get_context(self, query, top_k):
        return "Semantic context"

    def retrieve(self, query, top_k=3):
        return [{"content": "Chunk A"}]

    def ingest_text(self, content, metadata, document_id=None):
        self.ingest_calls.append((content, metadata, document_id))
        return document_id


def test_embedded_adapter_uses_direct_jira_context_lookup():
    adapter = EmbeddedRagAdapter(FakeEmbeddedService())

    context = adapter.get_jira_context("PROJ-123")

    assert "Jira content" in context
    assert "Confluence content" in context


def test_embedded_adapter_ingest_builds_stable_document_id():
    service = FakeEmbeddedService()
    adapter = EmbeddedRagAdapter(service)

    result = adapter.ingest("content", {"type": "jira_issue", "key": "PROJ-123"})

    assert result == "jira_issue:PROJ-123"
    assert service.ingest_calls[0][2] == "jira_issue:PROJ-123"


def test_external_adapter_posts_document_upsert():
    session = Mock()
    session.post.return_value.json.return_value = {"document_id": "jira_issue:PROJ-123"}
    session.post.return_value.raise_for_status.return_value = None
    adapter = ExternalRagAdapter(
        base_url="http://rag-service",
        timeout_seconds=2.0,
        session=session,
    )

    result = adapter.ingest("content", {"type": "jira_issue", "key": "PROJ-123"})

    assert result == "jira_issue:PROJ-123"
    session.post.assert_called_once()
    assert session.post.call_args.args[0] == "http://rag-service/documents/upsert"


def test_external_adapter_maps_retrieve_results():
    session = Mock()
    session.post.return_value.json.return_value = {
        "results": [
            {
                "content": "Context chunk",
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "metadata": {"type": "jira_issue"},
                "score": 0.9,
                "source_url": "https://jira.example/browse/PROJ-123",
            }
        ]
    }
    session.post.return_value.raise_for_status.return_value = None
    adapter = ExternalRagAdapter(
        base_url="http://rag-service",
        timeout_seconds=2.0,
        session=session,
    )

    chunks = adapter.retrieve("query", top_k=2, filters={"type": "jira_issue"})

    assert chunks[0]["content"] == "Context chunk"
    assert chunks[0]["metadata"]["type"] == "jira_issue"
    assert session.post.call_args.kwargs["json"]["filters"] == {"type": "jira_issue"}


def test_external_adapter_returns_empty_retrieve_results():
    session = Mock()
    session.post.return_value.json.return_value = {"results": []}
    session.post.return_value.raise_for_status.return_value = None
    adapter = ExternalRagAdapter(
        base_url="http://rag-service",
        timeout_seconds=2.0,
        session=session,
    )

    assert adapter.retrieve("query") == []
    assert adapter.get_context("query") is None


def test_external_adapter_wraps_validation_error_as_runtime_error():
    session = Mock()
    session.post.return_value.raise_for_status.side_effect = requests.HTTPError(
        "422 Client Error"
    )
    adapter = ExternalRagAdapter(
        base_url="http://rag-service",
        timeout_seconds=2.0,
        session=session,
    )

    with pytest.raises(RuntimeError, match="RAG service request failed"):
        adapter.ingest("content", {"type": "confluence_page"})


def test_external_adapter_fetches_document_by_id():
    session = Mock()
    session.get.return_value.json.return_value = {"document_id": "jira_issue:PROJ-123"}
    session.get.return_value.raise_for_status.return_value = None
    adapter = ExternalRagAdapter(
        base_url="http://rag-service",
        timeout_seconds=2.0,
        session=session,
    )

    assert adapter.get_document("jira_issue:PROJ-123")["document_id"] == "jira_issue:PROJ-123"
    session.get.assert_called_once()
    assert session.get.call_args.args[0] == "http://rag-service/documents/jira_issue:PROJ-123"


def test_external_adapter_wraps_timeout_as_runtime_error():
    session = Mock()
    session.post.side_effect = requests.Timeout("slow")
    adapter = ExternalRagAdapter(
        base_url="http://rag-service",
        timeout_seconds=2.0,
        session=session,
    )

    with pytest.raises(RuntimeError, match="RAG service request failed"):
        adapter.retrieve("query")
