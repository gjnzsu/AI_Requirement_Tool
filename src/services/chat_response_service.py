"""Shared LLM response execution for chat-oriented agent flows."""

from __future__ import annotations

import concurrent.futures
from typing import Callable, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


class ChatResponseService:
    """Generate chat replies with consistent timeout and error handling."""

    def __init__(self, llm_provider, provider_name: Optional[str] = None) -> None:
        self.llm_provider = llm_provider
        self.provider_name = (provider_name or "").lower()

    def generate_reply(
        self,
        *,
        messages: List[BaseMessage],
        user_input: str,
        system_prompt: str,
        timeout_seconds: Optional[float] = None,
        error_message_builder: Optional[Callable[[Exception], str]] = None,
        timeout_message: Optional[str] = None,
        fallback_error_message: Optional[str] = None,
    ) -> List[BaseMessage]:
        """Return a new message list with the model reply or a safe error message."""
        normalized_messages = list(messages)

        if not normalized_messages or not isinstance(normalized_messages[0], SystemMessage):
            normalized_messages = [SystemMessage(content=system_prompt)] + normalized_messages

        normalized_messages.append(HumanMessage(content=user_input))

        if not self.llm_provider or not hasattr(self.llm_provider, "invoke"):
            normalized_messages.append(
                AIMessage(
                    content=(
                        fallback_error_message
                        or "I apologize, but the AI service is not configured correctly."
                    )
                )
            )
            return normalized_messages

        effective_timeout = timeout_seconds or self._default_timeout_seconds()
        timeout_text = timeout_message or (
            "I apologize, but the request timed out. Please check your API key and "
            "network connection. The API may be slow or unavailable."
        )
        fallback_text = fallback_error_message or (
            "I apologize, but I encountered an unexpected error. Please try again later."
        )

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.llm_provider.invoke, normalized_messages)
                response = future.result(timeout=effective_timeout)
            normalized_messages.append(response)
        except concurrent.futures.TimeoutError:
            normalized_messages.append(AIMessage(content=timeout_text))
        except Exception as error:
            error_text = (
                error_message_builder(error)
                if error_message_builder is not None
                else fallback_text
            )
            normalized_messages.append(AIMessage(content=error_text))

        return normalized_messages

    def _default_timeout_seconds(self) -> float:
        if self.provider_name in {"openai", "deepseek"}:
            return 90.0
        if self.provider_name == "gemini":
            return 45.0
        return 60.0
