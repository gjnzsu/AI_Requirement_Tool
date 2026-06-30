"""Staged PM Status Agent service."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.application.ports import PmStatusReport
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
        r"\b(?:jira\s+project|project\s+key|project)\s*:?\s*[\"']?([A-Z][A-Z0-9]{1,9})[\"']?\b",
        re.IGNORECASE,
    )
    ISSUE_KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-\d+\b")
    FOR_PROJECT_PATTERN = re.compile(r"\bfor\s+([A-Z][A-Z0-9]{1,9})\b")
    PROJECT_KEY_STOP_WORDS = {
        "CONFLUENCE",
        "CURRENT",
        "DAILY",
        "JIRA",
        "PM",
        "PROJECT",
        "REPORT",
        "REVIEW",
        "SPACE",
        "SPRINT",
        "STATUS",
        "TODAY",
        "WEEKLY",
    }
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
        timestamp_provider: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.workflow_service = workflow_service
        self.default_project_key = default_project_key
        self.confluence_page_port = confluence_page_port
        self.timestamp_provider = timestamp_provider or self._current_utc_timestamp

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
            jira_jql=self._build_sprint_scope_jqls(project_key),
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

        title, body_markdown = self._build_confluence_publish_content(pending_state)
        result = self.confluence_page_port.create_page(
            title,
            body_markdown,
        )
        link = getattr(result, "link", None) or (result.get("link") if isinstance(result, dict) else "")
        title = getattr(result, "title", None) or title
        return ProjectStatusAgentTurnResult(
            response_text=f"Published PM status page: {title}\n{link}".strip(),
            response_kind="completed",
            pending_state=None,
            workflow_result=result,
            workflow_progress=[
                {"step": "pm_writeback", "label": "Publish PM status", "status": "completed", "detail": link}
            ],
        )

    def _build_confluence_publish_content(
        self,
        pending_state: Dict[str, Any],
    ) -> Tuple[str, str]:
        content = pending_state.get("suggested_confluence_content") or {}
        title = content.get("title", "PM Status Update")
        body_markdown = content.get("body_markdown", "")

        report_payload = pending_state.get("report")
        if isinstance(report_payload, dict):
            try:
                report = PmStatusReport(**report_payload)
                if report.suggested_confluence_content:
                    title = report.suggested_confluence_content.title
                body_markdown = report.to_markdown()
            except (TypeError, ValueError):
                pass

        return self._with_timestamp_suffix(title), body_markdown

    def _with_timestamp_suffix(self, title: str) -> str:
        timestamp = self.timestamp_provider()
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            timestamp_text = timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            timestamp_text = str(timestamp).strip()
        return f"{title} - {timestamp_text}" if timestamp_text else title

    @staticmethod
    def _current_utc_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

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
                if candidate not in self.PROJECT_KEY_STOP_WORDS:
                    return candidate
        return None

    def _build_sprint_scope_jqls(self, project_key: str) -> List[str]:
        jira_reader = getattr(self.workflow_service, "jira_reader", None)
        list_sprints = getattr(jira_reader, "list_sprints", None)
        if not callable(list_sprints):
            return [self._build_open_sprints_jql(project_key)]

        try:
            sprints = list_sprints(project_key, states=["active", "closed"])
        except Exception:
            return [self._build_open_sprints_jql(project_key)]

        active_sprint_ids = [
            str(sprint.get("id"))
            for sprint in sprints
            if str(sprint.get("state") or "").lower() == "active" and sprint.get("id") is not None
        ]
        latest_closed = self._latest_closed_sprint(sprints)

        jqls: List[str] = []
        if active_sprint_ids:
            jqls.append(
                f"project = {project_key} AND sprint in ({', '.join(active_sprint_ids)}) "
                "ORDER BY priority DESC, updated DESC"
            )
        if latest_closed and latest_closed.get("id") is not None:
            jqls.append(
                f"project = {project_key} AND sprint = {latest_closed['id']} "
                "ORDER BY priority DESC, updated DESC"
            )
        return jqls or [self._build_open_sprints_jql(project_key)]

    def _build_open_sprints_jql(self, project_key: str) -> str:
        return f"project = {project_key} AND sprint in openSprints() ORDER BY priority DESC, updated DESC"

    def _latest_closed_sprint(self, sprints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        closed_sprints = [
            sprint
            for sprint in sprints
            if str(sprint.get("state") or "").lower() == "closed" and sprint.get("id") is not None
        ]
        if not closed_sprints:
            return None
        return max(
            closed_sprints,
            key=lambda sprint: (
                str(sprint.get("completeDate") or sprint.get("endDate") or sprint.get("startDate") or ""),
                self._sprint_id_sort_value(sprint.get("id")),
            ),
        )

    def _sprint_id_sort_value(self, sprint_id: Any) -> int:
        try:
            return int(sprint_id or 0)
        except (TypeError, ValueError):
            return 0

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
