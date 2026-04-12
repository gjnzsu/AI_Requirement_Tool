"""Helper service for RAG ingestion and compact content formatting."""

from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, Optional

from src.utils.logger import get_logger


logger = get_logger("chatbot.rag_ingestion")


class RagIngestionService:
    """Encapsulate RAG ingestion side effects and compact content shaping."""

    def __init__(self, *, rag_service: Any) -> None:
        self.rag_service = rag_service

    def ingest(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Ingest text into the RAG knowledge base without blocking the main response."""
        if not self.rag_service:
            logger.debug("RAG service not available, skipping ingestion")
            return None

        doc_type = metadata.get("type", "unknown")
        doc_key = metadata.get("key", metadata.get("title", ""))
        custom_doc_id = f"{doc_type}:{doc_key}" if doc_key else None

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self.rag_service.ingest_text,
                    content,
                    metadata,
                    document_id=custom_doc_id,
                )
                try:
                    return future.result(timeout=10)
                except concurrent.futures.TimeoutError:
                    logger.warning("RAG ingestion timeout for %s: %s", doc_type, doc_key)
                    return None
        except Exception as error:
            logger.warning("Failed to ingest to RAG: %s", error)
            return None

    def simplify_confluence_content(
        self,
        *,
        issue_key: str,
        backlog_data: Dict[str, Any],
        evaluation: Dict[str, Any],
        confluence_link: str,
    ) -> str:
        """Create a compact, searchable text representation for Confluence ingestion."""
        parts = []

        summary = backlog_data.get("summary", "Untitled")
        parts.append(f"Confluence: {issue_key} - {summary}")
        parts.append(f"Link: {confluence_link}")

        priority = backlog_data.get("priority", "Medium")
        parts.append(f"Priority: {priority}")

        business_value = backlog_data.get("business_value", "")
        if business_value:
            truncated = (
                f"{business_value[:150]}..."
                if len(business_value) > 150
                else business_value
            )
            parts.append(f"Business Value: {truncated}")

        acceptance_criteria = backlog_data.get("acceptance_criteria", [])
        if acceptance_criteria:
            parts.append(f"Acceptance Criteria: {len(acceptance_criteria)} items")
            first_item = acceptance_criteria[0]
            if first_item:
                truncated = (
                    f"{first_item[:80]}..." if len(first_item) > 80 else first_item
                )
                parts.append(f"  - {truncated}")

        if evaluation and "overall_maturity_score" in evaluation:
            parts.append(f"Maturity Score: {evaluation['overall_maturity_score']}/100")
            detailed_scores = evaluation.get("detailed_scores", {})
            if detailed_scores:
                score_summary = ", ".join(
                    f"{key.replace('_', ' ')}: {value}"
                    for key, value in detailed_scores.items()
                )
                if len(score_summary) > 200:
                    score_summary = f"{score_summary[:200]}..."
                parts.append(f"Scores: {score_summary}")

        parts.append(f"Keywords: confluence page, {issue_key}, requirements, documentation")
        return "\n".join(parts)
