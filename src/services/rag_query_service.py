"""Application service for RAG-backed conversational flow."""

from __future__ import annotations

import concurrent.futures
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage

from src.agent.rag_nodes import (
    build_rag_error_message,
    build_rag_prompt,
    extract_chunk_contents,
    extract_jira_key,
    load_direct_jira_context,
)
from src.services.chat_response_service import ChatResponseService


class RagQueryService:
    """Handle RAG retrieval and response generation for query turns."""

    def __init__(self, *, rag_service: Any, chat_response_service: ChatResponseService) -> None:
        self.rag_service = rag_service
        self.chat_response_service = chat_response_service

    def handle(
        self,
        *,
        user_input: str,
        messages: List[BaseMessage],
    ) -> Dict[str, Any]:
        """Run retrieval, build grounded prompt text, and generate a reply."""
        prompt_input = user_input
        rag_context = None

        if self.rag_service:
            try:
                context_text = self._load_context(user_input)
                if context_text and context_text.strip():
                    prompt_input = build_rag_prompt(context_text, user_input)
                    chunks = self.rag_service.retrieve(user_input, top_k=3)
                    rag_context = extract_chunk_contents(chunks)
            except Exception:
                prompt_input = user_input

        updated_messages = self.chat_response_service.generate_reply(
            messages=messages,
            user_input=prompt_input,
            system_prompt=(
                "You are a helpful AI assistant. Use the provided context to answer "
                "questions accurately."
            ),
            error_message_builder=lambda error: build_rag_error_message(str(error)),
            fallback_error_message=build_rag_error_message("unexpected error"),
        )

        return {
            "messages": updated_messages,
            "rag_context": rag_context,
        }

    def _load_context(self, user_input: str) -> str | None:
        jira_key = extract_jira_key(user_input)
        if jira_key:
            direct_context = load_direct_jira_context(self.rag_service.vector_store, jira_key)
            if direct_context:
                return direct_context

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.rag_service.get_context, user_input, 3)
            try:
                return future.result(timeout=15.0)
            except concurrent.futures.TimeoutError:
                return None
