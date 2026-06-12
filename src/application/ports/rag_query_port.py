"""Ports for RAG retrieval behavior."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class RagQueryPort(Protocol):
    """Application-facing contract for RAG retrieval."""

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return source-aware chunks for a semantic query."""

    def get_context(self, query: str, top_k: int = 3) -> Optional[str]:
        """Return joined context text for a semantic query."""

    def get_jira_context(self, jira_key: str) -> Optional[str]:
        """Return exact Jira-key context when available."""
