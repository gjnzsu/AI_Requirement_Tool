"""DTOs for PM status agent reports and write-back suggestions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union


HEALTH_COLORS = {"green": "Green", "amber": "Amber", "red": "Red"}


@dataclass
class StatusItem:
    """A normalized PM status line item."""

    summary: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    severity: Optional[str] = None
    source_key: Optional[str] = None

    def __post_init__(self) -> None:
        self.summary = self.summary.strip()
        self.owner = _clean_optional(self.owner)
        self.due_date = _clean_optional(self.due_date)
        self.severity = _clean_optional(self.severity)
        self.source_key = _clean_optional(self.source_key)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"summary": self.summary}
        _set_optional(payload, "owner", self.owner)
        _set_optional(payload, "due_date", self.due_date)
        _set_optional(payload, "severity", self.severity)
        _set_optional(payload, "source_key", self.source_key)
        return payload


@dataclass
class SourceReference:
    """Traceability reference used to ground PM status judgments."""

    source_type: str
    key: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None

    def __post_init__(self) -> None:
        self.source_type = self.source_type.strip().lower()
        self.key = _clean_optional(self.key)
        self.title = _clean_optional(self.title)
        self.url = _clean_optional(self.url)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"source_type": self.source_type}
        _set_optional(payload, "key", self.key)
        _set_optional(payload, "title", self.title)
        _set_optional(payload, "url", self.url)
        return payload


@dataclass
class SuggestedJiraUpdate:
    """A Jira update recommendation that still requires human approval."""

    issue_key: str
    field: str
    suggested_value: str
    rationale: str
    current_value: Optional[str] = None

    def __post_init__(self) -> None:
        self.issue_key = self.issue_key.strip().upper()
        self.field = self.field.strip()
        self.current_value = _clean_optional(self.current_value)
        self.suggested_value = self.suggested_value.strip()
        self.rationale = self.rationale.strip()

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "issue_key": self.issue_key,
            "field": self.field,
            "suggested_value": self.suggested_value,
            "rationale": self.rationale,
        }
        _set_optional(payload, "current_value", self.current_value)
        return payload


@dataclass
class SuggestedConfluenceContent:
    """A Confluence status page draft that still requires approval."""

    title: str
    body_markdown: str
    space_key: Optional[str] = None
    parent_page_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.body_markdown = self.body_markdown.strip()
        self.space_key = _clean_optional(self.space_key)
        self.parent_page_id = _clean_optional(self.parent_page_id)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "title": self.title,
            "body_markdown": self.body_markdown,
        }
        _set_optional(payload, "space_key", self.space_key)
        _set_optional(payload, "parent_page_id", self.parent_page_id)
        return payload


StatusInput = Union[str, StatusItem, Dict[str, Any]]
SourceReferenceInput = Union[SourceReference, Dict[str, Any]]
SuggestedJiraUpdateInput = Union[SuggestedJiraUpdate, Dict[str, Any]]
SuggestedConfluenceContentInput = Union[SuggestedConfluenceContent, Dict[str, Any], None]


@dataclass
class PmStatusReport:
    """Structured output produced by the PM status agent."""

    project_key: str
    project_name: str
    time_window: str
    audience: str
    health: str
    executive_summary: str
    progress: Sequence[StatusInput] = field(default_factory=list)
    risks: Sequence[StatusInput] = field(default_factory=list)
    blockers: Sequence[StatusInput] = field(default_factory=list)
    decisions_needed: Sequence[StatusInput] = field(default_factory=list)
    owner_gaps: Sequence[StatusInput] = field(default_factory=list)
    next_actions: Sequence[StatusInput] = field(default_factory=list)
    suggested_jira_updates: Sequence[SuggestedJiraUpdateInput] = field(default_factory=list)
    suggested_confluence_content: SuggestedConfluenceContentInput = None
    stakeholder_update: str = ""
    source_references: Sequence[SourceReferenceInput] = field(default_factory=list)
    confidence_notes: Sequence[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.project_key = self.project_key.strip().upper()
        self.project_name = self.project_name.strip()
        self.time_window = self.time_window.strip()
        self.audience = self.audience.strip()
        self.health = _normalize_health(self.health)
        self.executive_summary = self.executive_summary.strip()
        self.progress = _normalize_status_items(self.progress)
        self.risks = _normalize_status_items(self.risks)
        self.blockers = _normalize_status_items(self.blockers)
        self.decisions_needed = _normalize_status_items(self.decisions_needed)
        self.owner_gaps = _normalize_status_items(self.owner_gaps)
        self.next_actions = _normalize_status_items(self.next_actions)
        self.suggested_jira_updates = [
            item if isinstance(item, SuggestedJiraUpdate) else SuggestedJiraUpdate(**item)
            for item in self.suggested_jira_updates
        ]
        self.suggested_confluence_content = _normalize_confluence_content(
            self.suggested_confluence_content
        )
        self.stakeholder_update = self.stakeholder_update.strip()
        self.source_references = [
            item if isinstance(item, SourceReference) else SourceReference(**item)
            for item in self.source_references
        ]
        self.confidence_notes = [note.strip() for note in self.confidence_notes if note.strip()]

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "project_key": self.project_key,
            "project_name": self.project_name,
            "time_window": self.time_window,
            "audience": self.audience,
            "health": self.health,
            "executive_summary": self.executive_summary,
            "progress": [item.to_dict() for item in self.progress],
            "risks": [item.to_dict() for item in self.risks],
            "blockers": [item.to_dict() for item in self.blockers],
            "decisions_needed": [item.to_dict() for item in self.decisions_needed],
            "owner_gaps": [item.to_dict() for item in self.owner_gaps],
            "next_actions": [item.to_dict() for item in self.next_actions],
            "suggested_jira_updates": [item.to_dict() for item in self.suggested_jira_updates],
            "stakeholder_update": self.stakeholder_update,
            "source_references": [item.to_dict() for item in self.source_references],
            "confidence_notes": list(self.confidence_notes),
        }
        if self.suggested_confluence_content is not None:
            payload["suggested_confluence_content"] = self.suggested_confluence_content.to_dict()
        else:
            payload["suggested_confluence_content"] = None
        return payload

    def to_markdown(self) -> str:
        sections = [
            f"# {self.project_name} Status",
            f"## Health: {self.health}",
            self.executive_summary,
            _render_items("Progress", self.progress),
            _render_items("Risks", self.risks),
            _render_items("Blockers", self.blockers),
            _render_items("Decisions Needed", self.decisions_needed),
            _render_items("Owner Gaps", self.owner_gaps),
            _render_items("Next Actions", self.next_actions),
        ]
        if self.stakeholder_update:
            sections.extend(["## Stakeholder Update", self.stakeholder_update])
        return "\n\n".join(section for section in sections if section)


def _normalize_health(value: str) -> str:
    health = value.strip().lower()
    if health not in HEALTH_COLORS:
        raise ValueError("health must be one of Green, Amber, or Red")
    return HEALTH_COLORS[health]


def _normalize_status_items(items: Sequence[StatusInput]) -> List[StatusItem]:
    normalized: List[StatusItem] = []
    for item in items:
        if isinstance(item, StatusItem):
            normalized.append(item)
        elif isinstance(item, str):
            normalized.append(StatusItem(summary=item))
        else:
            normalized.append(StatusItem(**item))
    return normalized


def _normalize_confluence_content(
    value: SuggestedConfluenceContentInput,
) -> Optional[SuggestedConfluenceContent]:
    if value is None or isinstance(value, SuggestedConfluenceContent):
        return value
    return SuggestedConfluenceContent(**value)


def _render_items(title: str, items: Sequence[StatusItem]) -> str:
    if not items:
        return ""
    lines = [f"## {title}"]
    for item in items:
        details = []
        if item.owner:
            details.append(f"owner: {item.owner}")
        if item.due_date:
            details.append(f"due: {item.due_date}")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"- {item.summary}{suffix}")
    return "\n".join(lines)


def _clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _set_optional(payload: Dict[str, Any], key: str, value: Optional[str]) -> None:
    if value is not None:
        payload[key] = value
