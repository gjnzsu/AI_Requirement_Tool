"""Adapter for the embedded in-process RAG implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.agent.rag_nodes import load_direct_jira_context


class EmbeddedRagAdapter:
    """Wrap the existing embedded RAG service behind application ports."""

    def __init__(self, rag_service: Any) -> None:
        self.rag_service = rag_service

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self.rag_service.retrieve(query, top_k=top_k)

    def get_context(self, query: str, top_k: int = 3) -> Optional[str]:
        return self.rag_service.get_context(query, top_k)

    def get_jira_context(self, jira_key: str) -> Optional[str]:
        vector_store = getattr(self.rag_service, "vector_store", None)
        if not vector_store:
            return None
        return load_direct_jira_context(vector_store, jira_key)

    def ingest(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        document_id = self._build_document_id(metadata)
        return self.rag_service.ingest_text(
            content,
            metadata,
            document_id=document_id,
        )

    def ingest_text(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None,
    ) -> Optional[str]:
        return self.rag_service.ingest_text(
            content,
            metadata,
            document_id=document_id or self._build_document_id(metadata),
        )

    @staticmethod
    def _build_document_id(metadata: Dict[str, Any]) -> Optional[str]:
        doc_type = metadata.get("type", "unknown")
        doc_key = metadata.get("key", metadata.get("title", ""))
        return f"{doc_type}:{doc_key}" if doc_key else None
