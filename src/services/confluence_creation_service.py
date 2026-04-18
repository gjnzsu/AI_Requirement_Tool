"""Standalone service for direct freeform Confluence page creation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage


class ConfluenceCreationService:
    """Draft and create a Confluence page directly from freeform user input."""

    def __init__(
        self,
        *,
        llm_provider: Any,
        confluence_page_port: Optional[Any],
    ) -> None:
        self.llm_provider = llm_provider
        self.confluence_page_port = confluence_page_port

    def handle(
        self,
        *,
        user_input: str,
        messages: List[Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        if not self.confluence_page_port:
            result = {"success": False, "error": "Confluence tool is not configured."}
            return {
                "message": "Confluence page creation is not available because the Confluence tool is not configured.",
                "confluence_result": result,
            }

        draft = self._draft_page(
            user_input=user_input,
            messages=messages,
            conversation_history=conversation_history,
        )
        page_title = draft["title"]
        confluence_content = draft["content"]

        raw_result = self.confluence_page_port.create_page(page_title, confluence_content)
        confluence_result = self._normalize_port_result(raw_result)

        if not confluence_result.get("success"):
            error_text = confluence_result.get("error", "Unknown error")
            return {
                "message": f"Failed to create Confluence page: {error_text}",
                "confluence_result": confluence_result,
            }

        page_id = str(confluence_result.get("id", ""))
        link = confluence_result.get("link", "")
        summary = draft.get("summary", "")
        rag_document = f"Confluence Page: {page_title}\nSummary: {summary}\nLink: {link}".strip()

        return {
            "message": f"Created Confluence page: {page_title}\nLink: {link}",
            "confluence_result": confluence_result,
            "rag_document": rag_document,
            "rag_metadata": {
                "type": "confluence_page",
                "title": page_title,
                "link": link,
                "page_id": page_id,
            },
        }

    def _draft_page(
        self,
        *,
        user_input: str,
        messages: List[Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, str]:
        response = self._generate_llm_response(
            system_prompt=(
                "You draft Confluence pages from freeform product and project notes. "
                "Return valid JSON with keys: title, content, summary. "
                "The content must be concise HTML suitable for a Confluence page body."
            ),
            user_prompt=self._build_user_prompt(
                user_input=user_input,
                messages=messages,
                conversation_history=conversation_history,
            ),
        )

        try:
            payload = json.loads(self._strip_json_fences(response))
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}

        title = str(payload.get("title") or "Untitled Page").strip() or "Untitled Page"
        content = str(payload.get("content") or f"<p>{user_input}</p>").strip() or f"<p>{user_input}</p>"
        summary = str(payload.get("summary") or user_input).strip() or user_input
        return {
            "title": title,
            "content": content,
            "summary": summary,
        }

    def _build_user_prompt(
        self,
        *,
        user_input: str,
        messages: List[Any],
        conversation_history: List[Dict[str, str]],
    ) -> str:
        recent_messages = []
        for message in messages[-4:]:
            content = getattr(message, "content", None)
            if content:
                recent_messages.append(str(content))

        recent_history = [
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in conversation_history[-4:]
        ]

        return (
            "Draft a Confluence page from the user's request.\n\n"
            f"Recent message context:\n{chr(10).join(recent_messages) or '(none)'}\n\n"
            f"Recent conversation history:\n{chr(10).join(recent_history) or '(none)'}\n\n"
            f"Latest user request:\n{user_input}\n"
        )

    def _generate_llm_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        invoke = getattr(self.llm_provider, "invoke", None)
        if callable(invoke):
            response = invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = getattr(response, "content", None)
            if isinstance(content, (str, bytes, bytearray)):
                return content.decode() if isinstance(content, (bytes, bytearray)) else content
            if isinstance(response, (str, bytes, bytearray)):
                return response.decode() if isinstance(response, (bytes, bytearray)) else response
            if content is not None:
                return str(content)
            return str(response)

        generate_response = getattr(self.llm_provider, "generate_response", None)
        if callable(generate_response):
            response = generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
            )
            return response.decode() if isinstance(response, (bytes, bytearray)) else response

        raise ValueError("Configured llm_provider does not support generate_response or invoke")

    @staticmethod
    def _strip_json_fences(response: str) -> str:
        cleaned = (response or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(line for line in lines if not line.strip().startswith("```")).strip()
        return cleaned

    @staticmethod
    def _normalize_port_result(result: Any) -> Dict[str, Any]:
        if result is None:
            return {}
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if isinstance(result, dict):
            return dict(result)

        payload: Dict[str, Any] = {"success": bool(getattr(result, "success", False))}
        if getattr(result, "page_id", None) is not None:
            payload["id"] = getattr(result, "page_id")
        if getattr(result, "title", None) is not None:
            payload["title"] = getattr(result, "title")
        if getattr(result, "link", None) is not None:
            payload["link"] = getattr(result, "link")
        if getattr(result, "error", None) is not None:
            payload["error"] = getattr(result, "error")
        if getattr(result, "tool_used", None) is not None:
            payload["tool_used"] = getattr(result, "tool_used")
        return payload
