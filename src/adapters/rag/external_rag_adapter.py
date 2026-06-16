"""HTTP adapter for the platform ai-rag-service lifecycle API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


class ExternalRagAdapter:
    """Call ai-rag-service lifecycle endpoints through the RAG ports."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        session: Optional[Any] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
        }
        if filters:
            payload["filters"] = filters
        response = self._post("/retrieve", payload)
        return [self._normalize_chunk(item) for item in response.get("results", [])]

    def get_context(self, query: str, top_k: int = 3) -> Optional[str]:
        chunks = self.retrieve(query, top_k=top_k)
        context = "\n\n".join(chunk.get("content", "") for chunk in chunks if chunk.get("content"))
        return context or None

    def get_jira_context(self, jira_key: str) -> Optional[str]:
        response = self._get(f"/context/jira/{jira_key}")
        chunks = [self._normalize_chunk(item) for item in response.get("results", [])]
        context = "\n\n".join(chunk.get("content", "") for chunk in chunks if chunk.get("content"))
        return context or None

    def get_document(self, document_id: str) -> Dict[str, Any]:
        return self._get(f"/documents/{document_id}")

    def ingest(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        payload = {
            "content": content,
            "metadata": self._normalize_metadata(metadata),
        }
        document_id = self._build_document_id(metadata)
        if document_id:
            payload["document_id"] = document_id
        response = self._post("/documents/upsert", payload)
        return response.get("document_id")

    def ingest_text(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None,
    ) -> Optional[str]:
        payload = {
            "content": content,
            "metadata": self._normalize_metadata(metadata),
        }
        if document_id:
            payload["document_id"] = document_id
        response = self._post("/documents/upsert", payload)
        return response.get("document_id")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            raise RuntimeError(f"RAG service request failed: {error}") from error

    def _get(self, path: str) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}{path}",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            raise RuntimeError(f"RAG service request failed: {error}") from error

    @staticmethod
    def _normalize_chunk(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "content": item.get("content", ""),
            "document_id": item.get("document_id", ""),
            "chunk_id": item.get("chunk_id", ""),
            "metadata": item.get("metadata", {}),
            "score": item.get("score"),
            "source_url": item.get("source_url", ""),
        }

    @staticmethod
    def _normalize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(metadata)
        if "url" not in normalized and normalized.get("link"):
            normalized["url"] = normalized["link"]
        if normalized.get("type") == "confluence_page" and not normalized.get("space_key"):
            normalized["space_key"] = normalized.get("space", "")
        return normalized

    @staticmethod
    def _build_document_id(metadata: Dict[str, Any]) -> Optional[str]:
        doc_type = metadata.get("type")
        if doc_type == "jira_issue" and metadata.get("key"):
            return f"jira_issue:{metadata['key']}"
        if doc_type == "confluence_page":
            if metadata.get("page_id"):
                return f"confluence_page:{metadata['page_id']}"
            if metadata.get("title"):
                return f"confluence_page:{metadata['title']}"
        return None
