"""Staged PM Status Agent service."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.services.pm_status_demo_scenarios import PM_STATUS_DEMO_SCENARIOS


@dataclass
class ProjectStatusAgentTurnResult:
    """Structured result for a single PM Status Agent turn."""

    response_text: str
    response_kind: str
    pending_state: Optional[Dict[str, Any]]
    workflow_result: Optional[Any] = None
    workflow_progress: Optional[List[Dict[str, Any]]] = None


class ProjectStatusAgentService:
    """Handle one PM Status Agent turn."""

    DEMO_SCENARIO_PATTERN = re.compile(
        r"\b(?:pm\s+)?demo\s+scenario\s*:\s*([a-z0-9-]+)\b",
        re.IGNORECASE,
    )
    EXPLICIT_PROJECT_PATTERN = re.compile(
        r"\b(?:jira\s+project|project\s+key|project)\s*:?\s*([A-Z][A-Z0-9]{1,9})\b",
        re.IGNORECASE,
    )
    ISSUE_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-\d+\b")
    FOR_PROJECT_PATTERN = re.compile(r"\bfor\s+([A-Z][A-Z0-9]{1,9})\b")
    CONFLUENCE_SPACE_PATTERN = re.compile(
        r"\b(?:confluence\s+space|space\s+key|space)\s*:?\s*([A-Z][A-Z0-9_-]{1,30})\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        workflow_service: Any,
        default_project_key: str = "",
        confluence_page_port: Optional[Any] = None,
    ) -> None:
        self.workflow_service = workflow_service
        self.default_project_key = default_project_key
        self.confluence_page_port = confluence_page_port

    def handle_turn(
        self,
        *,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        pending_state: Optional[Dict[str, Any]],
    ) -> ProjectStatusAgentTurnResult:
        if pending_state and pending_state.get("awaiting_confirmation"):
            return self._handle_confirmation_turn(user_input, pending_state)

        demo_snapshot = self._load_demo_scenario(user_input)
        if demo_snapshot:
            report = self.workflow_service.generate_report_from_snapshot(demo_snapshot["input"])
            return ProjectStatusAgentTurnResult(
                response_text=report.to_markdown(),
                response_kind="report",
                pending_state=None,
                workflow_result=report,
                workflow_progress=[
                    {"step": "pm_demo", "label": "Load PM demo scenario", "status": "completed"},
                    {"step": "pm_report", "label": "Generate PM status", "status": "completed"},
                ],
            )

        project_key = self._extract_project_key(user_input) or self.default_project_key or "PROJECT"
        confluence_space_key = self._extract_confluence_space_key(user_input)
        meeting_notes = self._extract_meeting_notes(user_input)
        report = self.workflow_service.generate_report(
            project_key=project_key,
            project_name=f"{project_key} Project",
            time_window=self._extract_time_window(user_input),
            audience=self._extract_audience(user_input),
            jira_jql=f"project = {project_key} ORDER BY priority DESC, updated DESC",
            confluence_query=project_key,
            confluence_space_key=confluence_space_key,
            meeting_notes=meeting_notes,
        )
        suggested_content = report.suggested_confluence_content
        if self.confluence_page_port and suggested_content:
            pending_payload = {
                "stage": "confirmation",
                "awaiting_confirmation": True,
                "report": report.to_dict(),
                "suggested_confluence_content": suggested_content.to_dict(),
            }
            return ProjectStatusAgentTurnResult(
                response_text=(
                    f"{report.to_markdown()}\n\n"
                    "Confluence status page draft is ready. "
                    "Reply with 'approve' to publish or 'cancel' to stop."
                ),
                response_kind="confirmation",
                pending_state=pending_payload,
                workflow_result=report,
                workflow_progress=[
                    {"step": "pm_report", "label": "Generate PM status", "status": "completed"},
                    {"step": "pm_approval", "label": "Await PM status approval", "status": "pending"},
                ],
            )
        return ProjectStatusAgentTurnResult(
            response_text=report.to_markdown(),
            response_kind="report",
            pending_state=None,
            workflow_result=report,
            workflow_progress=[
                {"step": "pm_report", "label": "Generate PM status", "status": "completed"}
            ],
        )

    def _handle_confirmation_turn(
        self,
        user_input: str,
        pending_state: Dict[str, Any],
    ) -> ProjectStatusAgentTurnResult:
        normalized_input = " ".join((user_input or "").lower().split())
        if normalized_input in {"cancel", "stop", "abort", "never mind", "do not publish"}:
            return ProjectStatusAgentTurnResult(
                response_text="Cancelled the PM status write-back. Nothing was published.",
                response_kind="cancelled",
                pending_state=None,
                workflow_progress=[
                    {"step": "pm_writeback", "label": "Publish PM status", "status": "cancelled"}
                ],
            )

        if normalized_input not in {"approve", "approved", "yes", "go ahead", "publish"}:
            return ProjectStatusAgentTurnResult(
                response_text="Please reply with 'approve' to publish or 'cancel' to stop.",
                response_kind="confirmation",
                pending_state=pending_state,
                workflow_progress=[
                    {"step": "pm_approval", "label": "Await PM status approval", "status": "pending"}
                ],
            )

        if not self.confluence_page_port:
            return ProjectStatusAgentTurnResult(
                response_text="Confluence write-back is not configured. Nothing was published.",
                response_kind="failed",
                pending_state=None,
                workflow_progress=[
                    {"step": "pm_writeback", "label": "Publish PM status", "status": "failed"}
                ],
            )

        content = pending_state.get("suggested_confluence_content") or {}
        result = self.confluence_page_port.create_page(
            content.get("title", "PM Status Update"),
            content.get("body_markdown", ""),
        )
        link = getattr(result, "link", None) or (result.get("link") if isinstance(result, dict) else "")
        title = getattr(result, "title", None) or content.get("title", "PM Status Update")
        return ProjectStatusAgentTurnResult(
            response_text=f"Published PM status page: {title}\n{link}".strip(),
            response_kind="completed",
            pending_state=None,
            workflow_result=result,
            workflow_progress=[
                {"step": "pm_writeback", "label": "Publish PM status", "status": "completed", "detail": link}
            ],
        )

    def _extract_project_key(self, text: str) -> Optional[str]:
        text = text or ""
        for pattern in (
            self.EXPLICIT_PROJECT_PATTERN,
            self.ISSUE_KEY_PATTERN,
            self.FOR_PROJECT_PATTERN,
        ):
            match = pattern.search(text)
            if match:
                candidate = match.group(1).upper()
                if candidate not in {"JIRA", "PROJECT", "CONFLUENCE", "SPACE"}:
                    return candidate
        return None

    def _extract_confluence_space_key(self, text: str) -> Optional[str]:
        match = self.CONFLUENCE_SPACE_PATTERN.search(text or "")
        return match.group(1).upper() if match else None

    def _load_demo_scenario(self, text: str) -> Optional[Dict[str, Any]]:
        match = self.DEMO_SCENARIO_PATTERN.search(text or "")
        if not match:
            return None
        scenario_id = match.group(1)
        scenario = PM_STATUS_DEMO_SCENARIOS.get(scenario_id)
        if not scenario:
            return None
        return copy.deepcopy(scenario)

    def _extract_time_window(self, text: str) -> str:
        normalized = (text or "").lower()
        if "weekly" in normalized or "this week" in normalized:
            return "This week"
        if "daily" in normalized or "today" in normalized:
            return "Today"
        return "Current status"

    def _extract_audience(self, text: str) -> str:
        normalized = text or ""
        if "steering" in normalized.lower():
            return "Steering Committee"
        if "weekly review" in normalized.lower():
            return "Weekly Delivery Review"
        return "Project stakeholders"

    def _extract_meeting_notes(self, text: str) -> List[str]:
        marker = "meeting notes:"
        lower = (text or "").lower()
        if marker not in lower:
            return []
        notes_text = text[lower.index(marker) + len(marker) :]
        return [line.strip(" -") for line in notes_text.splitlines() if line.strip(" -")]
