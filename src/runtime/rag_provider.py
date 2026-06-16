"""Runtime factory for RAG provider ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.adapters.rag import EmbeddedRagAdapter, ExternalRagAdapter


@dataclass
class RagPorts:
    """Selected RAG provider ports for the current runtime."""

    query_port: Optional[Any]
    ingestion_port: Optional[Any]
    provider: str


def build_rag_ports(*, config: Any, embedded_rag_service: Optional[Any]) -> RagPorts:
    """Build selected RAG query and ingestion ports."""
    provider = str(getattr(config, "RAG_PROVIDER", "embedded") or "embedded").lower()

    if provider == "external":
        base_url = getattr(config, "AI_RAG_SERVICE_URL", "")
        if not base_url:
            return RagPorts(query_port=None, ingestion_port=None, provider="external")
        adapter = ExternalRagAdapter(
            base_url=base_url,
            timeout_seconds=float(getattr(config, "AI_RAG_SERVICE_TIMEOUT_SECONDS", 10.0)),
        )
        return RagPorts(query_port=adapter, ingestion_port=adapter, provider="external")

    if embedded_rag_service is None:
        return RagPorts(query_port=None, ingestion_port=None, provider="embedded")

    adapter = EmbeddedRagAdapter(embedded_rag_service)
    return RagPorts(query_port=adapter, ingestion_port=adapter, provider="embedded")
