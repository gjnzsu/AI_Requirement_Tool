"""LLM-as-a-Judge review for approved requirement drafts."""

from __future__ import annotations

import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage


class RequirementJudgeService:
    """Produce advisory semantic quality feedback before Jira creation."""

    def __init__(self, llm_provider: Any) -> None:
        self.llm_provider = llm_provider

    def review(self, backlog_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self._generate_response(
            system_prompt=(
                "You are an expert requirement quality judge. Review approved "
                "requirement drafts for clarity, testability, scope readiness, "
                "business value, and ambiguity. Return only valid JSON."
            ),
            user_prompt=self._build_prompt(backlog_data),
        )
        payload = json.loads(self._strip_json_fences(response))
        if not isinstance(payload, dict):
            raise ValueError("Requirement judge returned a non-object payload.")

        payload.setdefault("overall_score", 0)
        payload.setdefault("decision", "needs_review")
        payload.setdefault("criteria_scores", {})
        payload.setdefault("findings", [])
        payload.setdefault("suggested_improvements", [])
        return payload

    def _generate_response(self, *, system_prompt: str, user_prompt: str) -> str:
        generate_response = getattr(self.llm_provider, "generate_response", None)
        if callable(generate_response):
            response = generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                json_mode=True,
                timeout=30.0,
            )
            return response.decode() if isinstance(response, (bytes, bytearray)) else response

        invoke = getattr(self.llm_provider, "invoke", None)
        if callable(invoke):
            response = invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
            content = getattr(response, "content", response)
            return content.decode() if isinstance(content, (bytes, bytearray)) else str(content)

        raise ValueError("Configured llm_provider does not support judge review.")

    @staticmethod
    def _build_prompt(backlog_data: Dict[str, Any]) -> str:
        return (
            "Review this requirement draft as advisory feedback before Jira creation.\n\n"
            f"{json.dumps(backlog_data, ensure_ascii=True, indent=2)}\n\n"
            "Return JSON with this shape:\n"
            "{\n"
            '  "overall_score": 0-100,\n'
            '  "decision": "pass|needs_review|weak",\n'
            '  "criteria_scores": {"clarity": 0-100, "testability": 0-100},\n'
            '  "findings": ["short actionable finding"],\n'
            '  "suggested_improvements": ["short improvement"]\n'
            "}"
        )

    @staticmethod
    def _strip_json_fences(response: str) -> str:
        return response.replace("```json", "").replace("```", "").strip()
