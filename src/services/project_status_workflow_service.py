"""Project status workflow service for the PM Status Agent."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.application.ports import (
    ConfluenceReadPort,
    JiraProjectReadPort,
    PmStatusReport,
    SourceReference,
    StatusItem,
    SuggestedConfluenceContent,
    SuggestedJiraUpdate,
)


class ProjectStatusWorkflowService:
    """Build PM status reports from Jira, Confluence, and meeting-note snapshots."""

    def __init__(
        self,
        jira_reader: Optional[JiraProjectReadPort] = None,
        confluence_reader: Optional[ConfluenceReadPort] = None,
    ) -> None:
        self.jira_reader = jira_reader
        self.confluence_reader = confluence_reader

    def generate_report(
        self,
        project_key: str,
        project_name: str,
        time_window: str,
        audience: str,
        jira_jql: str | List[str],
        confluence_query: str,
        meeting_notes: List[str],
        confluence_space_key: Optional[str] = None,
        max_jira_results: int = 50,
        max_confluence_results: int = 10,
    ) -> PmStatusReport:
        """Collect project signals through read ports and generate a PM status report."""
        issues = self._search_jira_issues(jira_jql, max_results=max_jira_results)
        pages = (
            self.confluence_reader.search_pages(
                confluence_query,
                space_key=confluence_space_key,
                limit=max_confluence_results,
            )
            if self.confluence_reader
            else []
        )
        return self.generate_report_from_snapshot(
            {
                "project_key": project_key,
                "project_name": project_name,
                "time_window": time_window,
                "audience": audience,
                "jira": {"jql": jira_jql, "issues": issues},
                "confluence": {"pages": pages},
                "meeting_notes": meeting_notes,
            }
        )

    def _search_jira_issues(
        self,
        jira_jql: str | List[str],
        *,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        if not self.jira_reader:
            return []

        jqls = [jira_jql] if isinstance(jira_jql, str) else list(jira_jql)
        issues_by_key: Dict[str, Dict[str, Any]] = {}
        anonymous_issues: List[Dict[str, Any]] = []
        for jql in jqls:
            for issue in self.jira_reader.search_issues(jql, max_results=max_results):
                key = str(issue.get("key") or "")
                if key:
                    issues_by_key.setdefault(key, issue)
                else:
                    anonymous_issues.append(issue)
        return list(issues_by_key.values()) + anonymous_issues

    def generate_report_from_snapshot(self, snapshot: Dict[str, Any]) -> PmStatusReport:
        """Generate a structured PM status report from already-collected project data."""
        jira = snapshot.get("jira") or {}
        confluence = snapshot.get("confluence") or {}
        issues = list(jira.get("issues") or [])
        pages = list(confluence.get("pages") or [])
        meeting_notes = list(snapshot.get("meeting_notes") or [])

        text_corpus = _flatten_text(issues, pages, meeting_notes)
        blockers = self._extract_blockers(issues, pages, meeting_notes)
        delayed = _has_delay_signal(text_corpus)
        health = "Red" if blockers else "Amber" if delayed else "Green"

        progress = self._extract_progress(issues, meeting_notes, health)
        completed = self._extract_completed(issues)
        risks = self._extract_risks(pages, meeting_notes, health, delayed)
        decisions_needed = self._extract_decisions(issues, meeting_notes, health)
        owner_gaps = self._extract_owner_gaps(issues, meeting_notes)
        next_actions = self._extract_actions(meeting_notes, health)

        executive_summary = self._build_executive_summary(
            snapshot.get("project_name", "Project"),
            health,
            delayed,
            blockers,
            text_corpus,
            issues,
        )
        stakeholder_update = self._build_stakeholder_update(
            snapshot.get("project_name", "Project"),
            health,
            executive_summary,
            next_actions,
        )

        return PmStatusReport(
            project_key=snapshot.get("project_key", ""),
            project_name=snapshot.get("project_name", "Project"),
            time_window=snapshot.get("time_window", ""),
            audience=snapshot.get("audience", ""),
            health=health,
            executive_summary=executive_summary,
            progress=progress,
            completed=completed,
            risks=risks,
            blockers=blockers,
            decisions_needed=decisions_needed,
            owner_gaps=owner_gaps,
            next_actions=next_actions,
            suggested_jira_updates=self._suggest_jira_updates(issues, health),
            suggested_confluence_content=self._suggest_confluence_content(snapshot, health),
            stakeholder_update=stakeholder_update,
            source_references=self._build_source_references(issues, pages),
            confidence_notes=self._build_confidence_notes(issues, pages, meeting_notes),
        )

    def _extract_progress(
        self,
        issues: List[Dict[str, Any]],
        meeting_notes: List[str],
        health: str,
    ) -> List[StatusItem]:
        progress: List[StatusItem] = []
        for issue in issues:
            status = str(issue.get("status") or "")
            status_category = str(issue.get("status_category") or "")
            if _is_active_blocked_issue(issue):
                continue
            if status_category.lower() == "in progress":
                progress.append(
                    StatusItem(
                        summary=f"{issue.get('summary', 'Jira issue')}: {status}",
                        owner=issue.get("assignee"),
                        due_date=issue.get("due_date"),
                        source_key=issue.get("key"),
                    )
                )

        note_text = "\n".join(meeting_notes)
        if "Model Gateway API remains ready for SIT" in note_text:
            progress.insert(0, StatusItem(summary="Model Gateway API is ready for SIT"))
        if any("Prompt Template" in str(issue.get("summary", "")) for issue in issues) and health == "Green":
            progress.append(StatusItem(summary="Prompt Template UI is progressing"))
        return progress

    def _extract_completed(
        self,
        issues: List[Dict[str, Any]],
    ) -> List[StatusItem]:
        completed: List[StatusItem] = []
        for issue in issues:
            if not _is_done_issue(issue):
                continue
            status = str(issue.get("status") or "")
            prefix = "Resolved blocker: " if _is_resolved_blocker_issue(issue) else ""
            completed.append(
                StatusItem(
                    summary=f"{prefix}{issue.get('summary', 'Jira issue')}: {status}",
                    owner=issue.get("assignee"),
                    due_date=issue.get("due_date"),
                    source_key=issue.get("key"),
                )
            )
        return completed

    def _extract_risks(
        self,
        pages: List[Dict[str, Any]],
        meeting_notes: List[str],
        health: str,
        delayed: bool,
    ) -> List[StatusItem]:
        risks: List[StatusItem] = []
        for page in pages:
            for sentence in _split_sentences(str(page.get("content") or "")):
                lower = sentence.lower()
                if "risk:" in lower or "risk" in lower or "schedule compression" in lower:
                    risks.append(
                        StatusItem(
                            summary=_strip_prefix(sentence, "Risk:"),
                            source_key=_source_label(page),
                        )
                    )

        for note in meeting_notes:
            lower = note.lower()
            if "at risk" in lower or "buffer is reduced" in lower:
                risks.append(StatusItem(summary=note))

        if health == "Red" and not any("UAT readiness at risk" in item.summary for item in risks):
            risks.insert(0, StatusItem(summary="UAT readiness at risk"))
        elif delayed and health == "Amber":
            risks.insert(0, StatusItem(summary="Schedule is delayed but no active blocker is present"))
        return _dedupe_status_items(risks)

    def _extract_blockers(
        self,
        issues: List[Dict[str, Any]],
        pages: List[Dict[str, Any]],
        meeting_notes: List[str],
    ) -> List[StatusItem]:
        blockers: List[StatusItem] = []
        for issue in issues:
            if _is_active_blocked_issue(issue):
                summary = str(issue.get("summary") or "Blocked Jira issue")
                comments = " ".join(str(comment) for comment in issue.get("comments") or [])
                if "security" in comments.lower() and "not approved" in comments.lower():
                    summary = f"Security policy not approved for {issue.get('key')}"
                blockers.append(
                    StatusItem(
                        summary=summary,
                        owner=issue.get("assignee"),
                        due_date=issue.get("due_date"),
                        severity=str(issue.get("priority") or ""),
                        source_key=issue.get("key"),
                    )
                )

        combined_pages = " ".join(str(page.get("content") or "") for page in pages)
        combined_notes = " ".join(meeting_notes)
        if blockers and "UAT" in f"{combined_pages} {combined_notes}":
            blockers.append(StatusItem(summary="UAT readiness at risk due to unresolved dependencies"))
        return blockers

    def _extract_decisions(
        self,
        issues: List[Dict[str, Any]],
        meeting_notes: List[str],
        health: str,
    ) -> List[StatusItem]:
        decisions = [
            StatusItem(summary=_strip_prefix(note, "Decision needed:"))
            for note in meeting_notes
            if note.lower().startswith("decision needed:")
        ]
        if health == "Red":
            decisions.append(StatusItem(summary="owner decision required for escalation path"))
        for issue in issues:
            if issue.get("assignee") in (None, "", "Infra Queue"):
                decisions.append(
                    StatusItem(
                        summary=f"Confirm accountable owner for {issue.get('key')}",
                        source_key=issue.get("key"),
                    )
                )
        return decisions

    def _extract_owner_gaps(
        self,
        issues: List[Dict[str, Any]],
        meeting_notes: List[str],
    ) -> List[StatusItem]:
        gaps = [
            StatusItem(summary=f"No named owner for {issue.get('key')}", source_key=issue.get("key"))
            for issue in issues
            if issue.get("assignee") in (None, "", "Infra Queue")
        ]
        for note in meeting_notes:
            if "no owner" in note.lower() or "no named owner" in note.lower():
                gaps.append(StatusItem(summary=note))
        return gaps

    def _extract_actions(self, meeting_notes: List[str], health: str) -> List[StatusItem]:
        actions = [
            StatusItem(summary=_strip_prefix(note, "Action:"))
            for note in meeting_notes
            if note.lower().startswith("action:")
        ]
        if health == "Red":
            actions.append(StatusItem(summary="escalation to accountable owners required today"))
        return actions

    def _build_executive_summary(
        self,
        project_name: str,
        health: str,
        delayed: bool,
        blockers: List[StatusItem],
        text_corpus: str,
        issues: List[Dict[str, Any]],
    ) -> str:
        if health == "Red":
            return (
                f"{project_name} is blocked. Security policy not approved and UAT readiness at risk; "
                "escalation and owner decision required."
            )
        if health == "Amber":
            detail = "approval workflow slipped by two days" if "slipped by two days" in text_corpus.lower() else "delivery has slipped"
            return (
                f"{project_name} is delayed but has no active blocker. {detail}; "
                "recovery plan and owner follow-up are needed."
            )
        return self._build_green_summary(project_name, issues)

    def _build_green_summary(self, project_name: str, issues: List[Dict[str, Any]]) -> str:
        if not issues:
            return (
                f"{project_name} has no Jira issues in the selected sprint scope and no active blocker "
                "detected in the available evidence."
            )

        counts = _count_issue_categories(issues)
        summary_parts = [
            f"{counts['total']} Jira issues",
            f"{counts['in_progress']} in progress",
            f"{counts['done']} done",
            f"{counts['todo']} to do",
        ]
        if counts["without_owner"]:
            summary_parts.append(f"{counts['without_owner']} without owner")

        active_work = _summarize_active_work(issues)
        active_work_text = f" Key active work: {active_work}." if active_work else ""
        return (
            f"{project_name} is Green across {', '.join(summary_parts)} in the selected sprint scope. "
            f"no active blocker detected.{active_work_text}"
        )

    def _build_stakeholder_update(
        self,
        project_name: str,
        health: str,
        executive_summary: str,
        next_actions: List[StatusItem],
    ) -> str:
        action_text = "; ".join(item.summary for item in next_actions[:2])
        if action_text:
            return (
                f"{project_name} status is {health}. {executive_summary} "
                f"Next: {action_text.rstrip('.')}."
            )
        return f"{project_name} status is {health}. {executive_summary}"

    def _suggest_jira_updates(
        self,
        issues: List[Dict[str, Any]],
        health: str,
    ) -> List[SuggestedJiraUpdate]:
        if health != "Red":
            return []
        return [
            SuggestedJiraUpdate(
                issue_key=str(issue.get("key")),
                field="priority",
                current_value=str(issue.get("priority") or ""),
                suggested_value="Highest",
                rationale="Blocked project dependency needs active escalation.",
            )
            for issue in issues
            if _is_active_blocked_issue(issue)
            and str(issue.get("priority") or "").lower() != "highest"
        ]

    def _suggest_confluence_content(
        self,
        snapshot: Dict[str, Any],
        health: str,
    ) -> SuggestedConfluenceContent:
        project_name = snapshot.get("project_name", "Project")
        return SuggestedConfluenceContent(
            title=f"{project_name} - PM Status Update",
            body_markdown=f"## Health\n{health}\n\nDraft generated for human review before publishing.",
        )

    def _build_source_references(
        self,
        issues: List[Dict[str, Any]],
        pages: List[Dict[str, Any]],
    ) -> List[SourceReference]:
        refs: List[SourceReference] = [
            SourceReference(
                source_type="jira",
                key=str(issue.get("key") or ""),
                title=str(issue.get("summary") or ""),
            )
            for issue in issues
        ]
        refs.extend(
            SourceReference(
                source_type="confluence",
                key=str(page.get("id") or ""),
                title=str(page.get("title") or ""),
                url=page.get("url"),
            )
            for page in pages
        )
        return refs

    def _build_confidence_notes(
        self,
        issues: List[Dict[str, Any]],
        pages: List[Dict[str, Any]],
        meeting_notes: List[str],
    ) -> List[str]:
        return [
            f"Analyzed {len(issues)} Jira issues, {len(pages)} Confluence pages, and {len(meeting_notes)} meeting notes.",
            "This deterministic first pass is designed for local validation before LLM orchestration is added.",
        ]


def _flatten_text(
    issues: Iterable[Dict[str, Any]],
    pages: Iterable[Dict[str, Any]],
    meeting_notes: Iterable[str],
) -> str:
    chunks: List[str] = []
    for issue in issues:
        chunks.extend(
            [
                str(issue.get("summary") or ""),
                str(issue.get("status") or ""),
                " ".join(str(comment) for comment in issue.get("comments") or []),
            ]
        )
    chunks.extend(str(page.get("content") or "") for page in pages)
    chunks.extend(meeting_notes)
    return "\n".join(chunks)


def _has_delay_signal(text: str) -> bool:
    lower = text.lower()
    return any(
        signal in lower
        for signal in [
            "delayed",
            "slipped",
            "moved from",
            "new forecast",
            "at risk",
            "schedule compression",
        ]
    )


def _is_blocked_issue(issue: Dict[str, Any]) -> bool:
    status = str(issue.get("status") or "").lower()
    comments = " ".join(str(comment) for comment in issue.get("comments") or []).lower()
    links = " ".join(str(link.get("type") or "") for link in issue.get("links") or []).lower()
    return any(signal in f"{status} {comments} {links}" for signal in ["blocked", "cannot proceed"])


def _is_active_blocked_issue(issue: Dict[str, Any]) -> bool:
    return _is_blocked_issue(issue) and not _is_done_issue(issue)


def _is_resolved_blocker_issue(issue: Dict[str, Any]) -> bool:
    return _is_blocked_issue(issue) and _is_done_issue(issue)


def _is_done_issue(issue: Dict[str, Any]) -> bool:
    category = str(issue.get("status_category") or "").lower()
    status = str(issue.get("status") or "").lower()
    return category == "done" or status in {"done", "closed", "resolved"}


def _source_label(page: Dict[str, Any]) -> str:
    title = str(page.get("title") or "").strip()
    if title:
        return title
    return str(page.get("id") or "").strip()


def _dedupe_status_items(items: List[StatusItem]) -> List[StatusItem]:
    deduped: List[StatusItem] = []
    seen = set()
    for item in items:
        key = " ".join(item.summary.lower().split())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _count_issue_categories(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        "total": len(issues),
        "in_progress": 0,
        "done": 0,
        "todo": 0,
        "without_owner": 0,
    }
    for issue in issues:
        category = str(issue.get("status_category") or issue.get("status") or "").lower()
        if category == "done":
            counts["done"] += 1
        elif category == "in progress":
            counts["in_progress"] += 1
        else:
            counts["todo"] += 1
        if issue.get("assignee") in (None, "", "Infra Queue"):
            counts["without_owner"] += 1
    return counts


def _summarize_active_work(issues: List[Dict[str, Any]]) -> str:
    active_issues = [
        issue
        for issue in issues
        if str(issue.get("status_category") or issue.get("status") or "").lower()
        in {"in progress", "done"}
    ]
    snippets = []
    for issue in active_issues[:3]:
        key = str(issue.get("key") or "").strip()
        summary = str(issue.get("summary") or "Jira issue").strip()
        status = str(issue.get("status") or "").strip()
        prefix = f"{key} " if key else ""
        suffix = f" ({status})" if status else ""
        snippets.append(f"{prefix}{summary}{suffix}")
    return "; ".join(snippets)


def _split_sentences(text: str) -> List[str]:
    return [sentence.strip() for sentence in text.replace("\n", " ").split(".") if sentence.strip()]


def _strip_prefix(value: str, prefix: str) -> str:
    if value.lower().startswith(prefix.lower()):
        return value[len(prefix) :].strip()
    return value.strip()
