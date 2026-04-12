"""Staged Requirement SDLC Agent service."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.utils.logger import get_logger


logger = get_logger("chatbot.requirement_sdlc_agent")


@dataclass
class RequirementSdlcAgentTurnResult:
    """Structured result for a single Requirement SDLC Agent turn."""

    response_text: str
    response_kind: str
    pending_state: Optional[Dict[str, Any]]
    workflow_result: Optional[Any] = None


class RequirementSdlcAgentService:
    """Own BA-guided intake, preview, confirmation, and execution handoff."""

    def __init__(self, *, llm_provider: Any, workflow_service: Any) -> None:
        self.llm_provider = llm_provider
        self.workflow_service = workflow_service

    def handle_turn(
        self,
        *,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        pending_state: Optional[Dict[str, Any]],
    ) -> RequirementSdlcAgentTurnResult:
        """Handle one Requirement SDLC Agent turn."""
        if pending_state and pending_state.get("awaiting_confirmation"):
            return self._handle_confirmation_turn(
                user_input=user_input,
                conversation_history=conversation_history,
                pending_state=pending_state,
            )

        return self._handle_analysis_turn(
            user_input=user_input,
            conversation_history=conversation_history,
            pending_state=pending_state,
        )

    def _handle_analysis_turn(
        self,
        *,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        pending_state: Optional[Dict[str, Any]],
    ) -> RequirementSdlcAgentTurnResult:
        analysis = self._analyze_requirement(
            user_input=user_input,
            conversation_history=conversation_history,
            pending_state=pending_state,
        )
        raw_draft = analysis.get("draft")
        if raw_draft is not None and not isinstance(raw_draft, dict):
            logger.warning(
                "Requirement lifecycle analysis returned non-dict draft payload: %s",
                type(raw_draft).__name__,
            )
            return self._build_controlled_question_result(
                message=(
                    "I couldn't safely interpret the draft yet. "
                    "Please clarify the requirement or restate the revision you want."
                ),
                pending_state=pending_state,
            )
        draft = self._normalize_draft(
            raw_draft,
            prior_draft=(pending_state or {}).get("draft"),
        )
        status = analysis.get("status", "needs_information")
        assistant_message = self._normalize_text_field(
            analysis.get("assistant_message"),
            default="I need a bit more detail before I can prepare the requirement draft.",
        )

        if status == "needs_information":
            return RequirementSdlcAgentTurnResult(
                response_text=assistant_message,
                response_kind="question",
                pending_state={
                    "stage": "analysis",
                    "awaiting_confirmation": False,
                    "draft": draft,
                    "open_questions": draft.get("open_questions", []),
                },
            )

        if status != "ready_for_confirmation":
            logger.warning("Unexpected requirement lifecycle analysis status: %s", status)
            return self._build_controlled_question_result(
                message=(
                    "I couldn't safely interpret the draft status yet. "
                    "Please clarify the requirement or restate the revision you want."
                ),
                pending_state=pending_state,
                draft=draft,
            )

        return RequirementSdlcAgentTurnResult(
            response_text=self._build_preview(draft, assistant_message),
            response_kind="preview",
            pending_state={
                "stage": "confirmation",
                "awaiting_confirmation": True,
                "draft": draft,
            },
        )

    def _handle_confirmation_turn(
        self,
        *,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        pending_state: Dict[str, Any],
    ) -> RequirementSdlcAgentTurnResult:
        normalized_input = " ".join(user_input.lower().split())
        if normalized_input in {"approve", "approved", "yes", "go ahead", "proceed"}:
            workflow_result = self.workflow_service.execute_backlog_data(
                pending_state["draft"]
            )
            return RequirementSdlcAgentTurnResult(
                response_text=workflow_result.response_text,
                response_kind="completed",
                pending_state=None,
                workflow_result=workflow_result,
            )

        if normalized_input in {
            "cancel",
            "stop",
            "abort",
            "never mind",
            "do not create anything",
            "don't create anything",
        }:
            return RequirementSdlcAgentTurnResult(
                response_text="Cancelled the requirement lifecycle draft. Nothing was created.",
                response_kind="cancelled",
                pending_state=None,
            )

        revised_state = copy.deepcopy(pending_state)
        revised_state["stage"] = "analysis"
        revised_state["awaiting_confirmation"] = False
        revised_state["revision_request"] = user_input
        return self._handle_analysis_turn(
            user_input=user_input,
            conversation_history=conversation_history,
            pending_state=revised_state,
        )

    def _analyze_requirement(
        self,
        *,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        pending_state: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            history_lines = [
                f"{message.get('role', 'user')}: {message.get('content', '')}"
                for message in conversation_history[-8:]
            ]
            pending_context = json.dumps(pending_state or {}, ensure_ascii=True)
            user_prompt = (
                "Analyze the requirement request and respond with valid JSON.\n\n"
                f"Conversation history:\n{chr(10).join(history_lines) or '(none)'}\n\n"
                f"Pending draft state:\n{pending_context}\n\n"
                f"Latest user input:\n{user_input}\n\n"
                "Return JSON with keys: status, assistant_message, draft.\n"
                "Allowed status values: ready_for_confirmation, needs_information.\n"
                "The draft should include summary, problem_goal, business_value, scope_notes, "
                "acceptance_criteria, assumptions, open_questions, priority, invest_analysis, description."
            )
            response = self._generate_llm_response(
                system_prompt=(
                    "You are a senior business analyst helping turn chat input into a "
                    "reviewable requirement draft. Ask concise follow-up questions when the "
                    "request is underspecified. Otherwise prepare a pragmatic draft."
                ),
                user_prompt=user_prompt,
            )
            payload = json.loads(self._strip_json_fences(response))
            if not isinstance(payload, dict):
                raise ValueError("Requirement lifecycle analysis must return a JSON object")
            return payload
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            logger.warning(
                "Requirement lifecycle analysis failed to parse safely: %s",
                error,
            )
            return {
                "status": "needs_information",
                "assistant_message": (
                    "I couldn't safely interpret the draft yet. "
                    "Please clarify the requirement or restate the revision you want."
                ),
                "draft": (pending_state or {}).get("draft") or {},
            }

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

    def _normalize_draft(
        self,
        draft: Optional[Dict[str, Any]],
        *,
        prior_draft: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        base: Dict[str, Any] = {}

        if isinstance(prior_draft, dict):
            base.update(copy.deepcopy(prior_draft))
        elif prior_draft is not None:
            logger.warning(
                "Requirement lifecycle prior draft had unexpected type: %s",
                type(prior_draft).__name__,
            )

        if isinstance(draft, dict):
            base.update(copy.deepcopy(draft))
        elif draft is not None:
            logger.warning(
                "Requirement lifecycle draft had unexpected type during normalization: %s",
                type(draft).__name__,
            )

        acceptance_criteria = base.get("acceptance_criteria") or []
        assumptions = base.get("assumptions") or []
        open_questions = base.get("open_questions") or []

        normalized = {
            "summary": self._normalize_text_field(base.get("summary")),
            "problem_goal": self._normalize_text_field(base.get("problem_goal")),
            "business_value": self._normalize_text_field(base.get("business_value")),
            "scope_notes": self._normalize_text_field(base.get("scope_notes")),
            "acceptance_criteria": self._normalize_list(acceptance_criteria),
            "assumptions": self._normalize_list(assumptions),
            "open_questions": self._normalize_list(open_questions),
            "priority": self._normalize_text_field(
                base.get("priority"),
                default="Medium",
            ),
            "invest_analysis": self._normalize_text_field(base.get("invest_analysis")),
        }
        normalized["description"] = self._build_jira_description(normalized)
        return normalized

    def _normalize_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value is None:
            return []
        text = str(value).strip()
        return [text] if text else []

    def _normalize_text_field(self, value: Any, *, default: str = "") -> str:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    def _build_jira_description(self, draft: Dict[str, Any]) -> str:
        sections = []
        if draft.get("problem_goal"):
            sections.append(f"Problem / Goal: {draft['problem_goal']}")
        if draft.get("business_value"):
            sections.append(f"Business Value: {draft['business_value']}")
        if draft.get("scope_notes"):
            sections.append(f"Scope Notes: {draft['scope_notes']}")
        if draft.get("acceptance_criteria"):
            criteria = "\n".join(
                f"- {criterion}" for criterion in draft["acceptance_criteria"]
            )
            sections.append(f"Acceptance Criteria:\n{criteria}")
        if draft.get("assumptions"):
            assumptions = "\n".join(
                f"- {assumption}" for assumption in draft["assumptions"]
            )
            sections.append(f"Assumptions:\n{assumptions}")
        if draft.get("invest_analysis"):
            sections.append(f"INVEST Analysis: {draft['invest_analysis']}")
        return "\n\n".join(sections)

    def _build_preview(self, draft: Dict[str, Any], assistant_message: Any) -> str:
        preview_lines = []
        safe_assistant_message = self._normalize_text_field(assistant_message)
        if safe_assistant_message:
            preview_lines.append(safe_assistant_message)
            preview_lines.append("")

        preview_lines.extend(
            [
                "Requirement Draft Preview",
                f"Summary: {draft.get('summary', '(missing)')}",
                f"Problem / Goal: {draft.get('problem_goal', '(missing)')}",
                f"Business Value: {draft.get('business_value', '(missing)')}",
                f"Scope Notes: {draft.get('scope_notes', '(none)')}",
                f"Priority: {draft.get('priority', 'Medium')}",
            ]
        )

        if draft.get("acceptance_criteria"):
            preview_lines.append("Acceptance Criteria:")
            preview_lines.extend(
                f"- {criterion}" for criterion in draft["acceptance_criteria"]
            )

        if draft.get("assumptions"):
            preview_lines.append("Assumptions:")
            preview_lines.extend(f"- {assumption}" for assumption in draft["assumptions"])

        if draft.get("open_questions"):
            preview_lines.append("Open Questions:")
            preview_lines.extend(
                f"- {question}" for question in draft["open_questions"]
            )

        preview_lines.extend(
            [
                "",
                "Reply with 'approve' to execute, 'cancel' to stop, or describe a revision.",
            ]
        )
        return "\n".join(preview_lines)

    def _strip_json_fences(self, response: str) -> str:
        return response.replace("```json", "").replace("```", "").strip()

    def _build_controlled_question_result(
        self,
        *,
        message: str,
        pending_state: Optional[Dict[str, Any]],
        draft: Optional[Dict[str, Any]] = None,
    ) -> RequirementSdlcAgentTurnResult:
        safe_draft = self._normalize_draft(
            draft,
            prior_draft=(pending_state or {}).get("draft"),
        )
        return RequirementSdlcAgentTurnResult(
            response_text=message,
            response_kind="question",
            pending_state={
                "stage": "analysis",
                "awaiting_confirmation": False,
                "draft": safe_draft,
                "open_questions": safe_draft.get("open_questions", []),
            },
        )
