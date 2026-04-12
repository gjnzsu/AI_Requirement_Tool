"""Application service for general conversational flow."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage

from src.agent.general_chat_nodes import (
    build_confluence_page_context,
    build_general_chat_error_message,
    parse_confluence_page_reference,
)
from src.services.chat_response_service import ChatResponseService


class GeneralChatService:
    """Handle general chat prompt enrichment and LLM response execution."""

    def __init__(
        self,
        *,
        chat_response_service: ChatResponseService,
        retrieve_confluence_page_info=None,
    ) -> None:
        self.chat_response_service = chat_response_service
        self.retrieve_confluence_page_info = retrieve_confluence_page_info

    def handle(
        self,
        *,
        user_input: str,
        messages: List[BaseMessage],
        confluence_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a general chat turn and return updated messages."""
        page_id, page_title = parse_confluence_page_reference(
            user_input,
            confluence_result,
        )

        page_info = None
        enriched_input = user_input
        if (page_id or page_title) and self.retrieve_confluence_page_info:
            page_info = self.retrieve_confluence_page_info(
                page_id=page_id,
                page_title=page_title,
            )
            if page_info.get("success"):
                enriched_input = user_input + build_confluence_page_context(page_info)

        updated_messages = self.chat_response_service.generate_reply(
            messages=messages,
            user_input=enriched_input,
            system_prompt=(
                "You are a helpful, friendly, and knowledgeable AI assistant. "
                "You provide clear, concise, and accurate responses."
            ),
            error_message_builder=lambda error: build_general_chat_error_message(
                error,
                self.chat_response_service.provider_name,
            )[0],
            fallback_error_message=(
                "I apologize, but I encountered an unexpected error. "
                "Please try again, or check your configuration if the problem persists."
            ),
        )

        return {
            "messages": updated_messages,
            "page_info": page_info,
        }
