"""Port for RAG ingestion side effects."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class RagIngestionPort(Protocol):
    """Application-facing contract for knowledge ingestion."""

    def ingest(self, content: str, metadata: Dict[str, Any]) -> Any:
        """Persist content and metadata into the RAG knowledge store."""

