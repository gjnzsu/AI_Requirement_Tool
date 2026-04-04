"""Helper functions for RAG query node context and response handling."""

import re
from typing import Any, Dict, Iterable, List, Optional


JIRA_KEY_PATTERN = r"\b([A-Z]{2,10}-\d+)\b"


def extract_jira_key(user_input: str) -> Optional[str]:
    """Extract a Jira issue key from the user's input, if one is present."""
    match = re.search(JIRA_KEY_PATTERN, user_input or "")
    return match.group(1) if match else None


def load_direct_jira_context(vector_store: Any, jira_key: str) -> Optional[str]:
    """Load Jira and related Confluence documents directly by issue key."""
    direct_context_parts = []

    jira_doc = vector_store.get_document(f"jira_issue:{jira_key}")
    if jira_doc:
        direct_context_parts.append(f"=== Jira Issue Content ===\n{jira_doc['content']}")

    for doc in vector_store.list_documents():
        doc_id = doc.get("id", "")
        if doc_id.startswith("confluence_page:") and jira_key in doc_id:
            confluence_doc = vector_store.get_document(doc_id)
            if confluence_doc:
                direct_context_parts.append(
                    f"=== Related Confluence Page ===\n{confluence_doc['content']}"
                )
            break

    return "\n\n".join(direct_context_parts) if direct_context_parts else None


def build_rag_prompt(context_text: str, user_input: str) -> str:
    """Build the final RAG-grounded user prompt."""
    return f"""
                    {context_text}

                    User Question: {user_input}

                    Please answer the user's question using the provided context.
                    If the context doesn't contain enough information, say so and provide
                    a general answer based on your knowledge.
                    """


def extract_chunk_contents(chunks: Iterable[Dict[str, Any]]) -> List[str]:
    """Extract chunk text values while preserving empty placeholders."""
    return [chunk.get("content", "") for chunk in chunks]


def build_rag_error_message(error_text: str) -> str:
    """Map raw RAG/LLM error text to a user-safe message."""
    normalized_error = (error_text or "").lower()
    if "timeout" in normalized_error:
        return "I apologize, but the request timed out. Please try again."
    if "connection" in normalized_error or "network" in normalized_error:
        return (
            "I apologize, but there was a network connectivity issue. "
            "Please check your connection and try again."
        )
    if "auth" in normalized_error or "unauthorized" in normalized_error:
        return (
            "I apologize, but there was an authentication issue. "
            "Please check your API configuration."
        )
    return (
        "I apologize, but I encountered an unexpected error. "
        "Please try again or rephrase your question."
    )
