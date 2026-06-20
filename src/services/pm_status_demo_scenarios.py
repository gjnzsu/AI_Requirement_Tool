"""Packaged PM Status Agent demo scenarios.

These fixtures are runtime data for the PM demo buttons. Keep them under ``src``
so Docker and GKE deployments include them even when OpenSpec artifacts are
excluded from the build context.
"""

from __future__ import annotations

from typing import Any, Dict


PM_STATUS_DEMO_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "scenario-01-on-track": {
        "id": "scenario-01-on-track",
        "name": "AI Platform Model Gateway SIT Readiness - On Track",
        "expected": {
            "health": "Green",
            "summary": "Project is progressing as planned with no material blockers.",
            "must_include": [
                "Model Gateway API is ready for SIT",
                "Prompt Template UI is progressing",
                "no active blocker",
                "prepare SIT entry checklist",
            ],
            "must_not_include": ["blocked", "critical escalation", "UAT date at risk"],
        },
        "input": {
            "project_key": "AIP",
            "project_name": "Enterprise AI Platform MVP",
            "time_window": "Past 24h",
            "audience": "IT Director and AI Platform Sponsor",
            "jira": {
                "jql": "project = AIP AND fixVersion = MVP-1 ORDER BY priority DESC",
                "issues": [
                    {
                        "key": "AIP-102",
                        "summary": "Build Model Gateway API",
                        "status": "In Review",
                        "status_category": "In Progress",
                        "assignee": "Maya Chen",
                        "due_date": "2026-06-22",
                        "priority": "High",
                        "comments": [
                            "Dev complete. Code review has one minor naming comment.",
                            "SIT deployment package will be ready tomorrow morning.",
                        ],
                        "links": [],
                    },
                    {
                        "key": "AIP-118",
                        "summary": "Prompt Template Management UI",
                        "status": "In Progress",
                        "status_category": "In Progress",
                        "assignee": "Leo Wang",
                        "due_date": "2026-06-24",
                        "priority": "Medium",
                        "comments": [
                            "List page and create template form are complete.",
                            "Approval workflow UI is scheduled for tomorrow.",
                        ],
                        "links": [],
                    },
                    {
                        "key": "AIP-130",
                        "summary": "Define logging schema for AI requests",
                        "status": "Done",
                        "status_category": "Done",
                        "assignee": "Nina Patel",
                        "due_date": "2026-06-20",
                        "priority": "Medium",
                        "comments": [
                            "Schema reviewed with Observability and Security.",
                            "Confluence page updated with masking fields.",
                        ],
                        "links": [],
                    },
                ],
            },
            "confluence": {
                "pages": [
                    {
                        "id": "873001",
                        "title": "Enterprise AI Platform MVP - Delivery Plan",
                        "url": "https://example.atlassian.net/wiki/spaces/AIP/pages/873001",
                        "content": (
                            "MVP-1 remains on track for SIT entry on 2026-06-23. UAT target remains 2026-06-28. "
                            "Current focus: Model Gateway, Prompt Template Management, logging schema, and SIT "
                            "readiness checklist."
                        ),
                    },
                    {
                        "id": "873019",
                        "title": "AI Platform RAID Log",
                        "url": "https://example.atlassian.net/wiki/spaces/AIP/pages/873019",
                        "content": (
                            "No open blockers. Risks are being monitored: prompt approval UX complexity and SIT "
                            "test data preparation. Owners assigned for all current actions."
                        ),
                    },
                ],
            },
            "meeting_notes": [
                "Engineering standup confirmed Model Gateway API remains ready for SIT package handoff tomorrow.",
                "Security confirmed logging masking fields are acceptable for SIT.",
                "Product owner confirmed demo scope remains Model Gateway request flow and prompt template creation.",
                "Action: PM to prepare SIT entry checklist by 2026-06-21.",
            ],
        },
    },
    "scenario-02-delayed-no-blocker": {
        "id": "scenario-02-delayed-no-blocker",
        "name": "AI Platform Prompt Approval Flow - Delayed Without Blocker",
        "expected": {
            "health": "Amber",
            "summary": "Project is delayed but not blocked; recovery plan and owner follow-up are needed.",
            "must_include": [
                "delayed",
                "no active blocker",
                "recovery plan",
                "approval workflow slipped by two days",
            ],
            "must_not_include": ["blocked by Security", "cannot proceed", "Red"],
        },
        "input": {
            "project_key": "AIP",
            "project_name": "Enterprise AI Platform MVP",
            "time_window": "This week",
            "audience": "Weekly Delivery Review",
            "jira": {
                "jql": "project = AIP AND labels in (prompt-management) ORDER BY updated DESC",
                "issues": [
                    {
                        "key": "AIP-118",
                        "summary": "Prompt Template Management UI",
                        "status": "In Progress",
                        "status_category": "In Progress",
                        "assignee": "Leo Wang",
                        "due_date": "2026-06-24",
                        "priority": "High",
                        "comments": [
                            "Approval workflow UI took longer than expected because reviewer role mapping changed.",
                            "No external blocker. Frontend and backend owners agreed on revised API contract.",
                            "New forecast: complete by 2026-06-26.",
                        ],
                        "links": [
                            {
                                "type": "relates to",
                                "key": "AIP-145",
                                "summary": "Reviewer role mapping for prompt approval",
                            }
                        ],
                    },
                    {
                        "key": "AIP-145",
                        "summary": "Reviewer role mapping for prompt approval",
                        "status": "Done",
                        "status_category": "Done",
                        "assignee": "Priya Shah",
                        "due_date": "2026-06-19",
                        "priority": "Medium",
                        "comments": ["Role mapping finalized with Product and Security."],
                        "links": [],
                    },
                    {
                        "key": "AIP-149",
                        "summary": "Approval API contract update",
                        "status": "In Progress",
                        "status_category": "In Progress",
                        "assignee": "Daniel Kim",
                        "due_date": "2026-06-21",
                        "priority": "Medium",
                        "comments": [
                            "Endpoint shape confirmed. Implementation in progress.",
                            "No dependency issue at this time.",
                        ],
                        "links": [],
                    },
                ],
            },
            "confluence": {
                "pages": [
                    {
                        "id": "873001",
                        "title": "Enterprise AI Platform MVP - Delivery Plan",
                        "url": "https://example.atlassian.net/wiki/spaces/AIP/pages/873001",
                        "content": (
                            "Prompt approval flow moved from 2026-06-24 to 2026-06-26. UAT target remains "
                            "2026-06-28 if SIT confirms no Sev1 defects. Recovery plan: keep happy-path demo "
                            "scope, add approval edge cases after UAT entry."
                        ),
                    },
                    {
                        "id": "873019",
                        "title": "AI Platform RAID Log",
                        "url": "https://example.atlassian.net/wiki/spaces/AIP/pages/873019",
                        "content": (
                            "Risk: prompt approval flow schedule compression. No blocker. Mitigation: narrow "
                            "demo to happy path and confirm revised API contract by 2026-06-21."
                        ),
                    },
                ],
            },
            "meeting_notes": [
                "Prompt approval workflow slipped by two days due to reviewer role mapping changes.",
                "Security and Product agreed the role mapping is now finalized.",
                "Team says there is no active blocker, but schedule buffer is reduced.",
                "Action: Engineering Lead to publish recovery plan by 2026-06-20.",
                "Action: Product Owner to confirm whether edge-case approval scenarios can move after UAT entry.",
            ],
        },
    },
    "scenario-03-delayed-with-blocker": {
        "id": "scenario-03-delayed-with-blocker",
        "name": "AI Platform UAT Readiness - Delayed With Blocker",
        "expected": {
            "health": "Red",
            "summary": "Project is delayed and blocked by unresolved security and environment dependencies.",
            "must_include": [
                "blocked",
                "Security policy not approved",
                "UAT readiness at risk",
                "escalation",
                "owner decision required",
            ],
            "must_not_include": ["on track", "no active blocker", "Green"],
        },
        "input": {
            "project_key": "AIP",
            "project_name": "Enterprise AI Platform MVP",
            "time_window": "Past 48h",
            "audience": "IT Director, Security Manager, AI Platform Sponsor",
            "jira": {
                "jql": "project = AIP AND fixVersion = MVP-1 AND statusCategory != Done ORDER BY priority DESC",
                "issues": [
                    {
                        "key": "AIP-121",
                        "summary": "Automate Azure OpenAI key rotation",
                        "status": "Blocked",
                        "status_category": "In Progress",
                        "assignee": "Omar Ali",
                        "due_date": "2026-06-20",
                        "priority": "Highest",
                        "comments": [
                            "Blocked until Security approves secret rotation policy.",
                            "Cannot proceed with UAT environment because key rotation approach is not approved.",
                            "Manual workaround proposed but not yet accepted.",
                        ],
                        "links": [
                            {
                                "type": "blocks",
                                "key": "AIP-134",
                                "summary": "Provision UAT environment",
                            }
                        ],
                    },
                    {
                        "key": "AIP-134",
                        "summary": "Provision UAT environment",
                        "status": "Blocked",
                        "status_category": "In Progress",
                        "assignee": "Infra Queue",
                        "due_date": "2026-06-21",
                        "priority": "High",
                        "comments": [
                            "Network whitelist approval is still pending.",
                            "Environment provisioning cannot complete without Security and Network approvals.",
                            "No named owner for final Network approval.",
                        ],
                        "links": [
                            {
                                "type": "is blocked by",
                                "key": "AIP-121",
                                "summary": "Automate Azure OpenAI key rotation",
                            }
                        ],
                    },
                    {
                        "key": "AIP-151",
                        "summary": "Define AI usage audit trail owner",
                        "status": "Open",
                        "status_category": "To Do",
                        "assignee": None,
                        "due_date": "2026-06-20",
                        "priority": "High",
                        "comments": [
                            "Data Governance and AI Platform have not agreed ownership.",
                            "Governance sign-off cannot complete until owner is assigned.",
                        ],
                        "links": [],
                    },
                ],
            },
            "confluence": {
                "pages": [
                    {
                        "id": "873001",
                        "title": "Enterprise AI Platform MVP - Delivery Plan",
                        "url": "https://example.atlassian.net/wiki/spaces/AIP/pages/873001",
                        "content": (
                            "UAT target is 2026-06-28. Entry criteria: key rotation policy approved, UAT "
                            "environment provisioned, audit trail owner assigned, logging schema signed off."
                        ),
                    },
                    {
                        "id": "873019",
                        "title": "AI Platform RAID Log",
                        "url": "https://example.atlassian.net/wiki/spaces/AIP/pages/873019",
                        "content": (
                            "Issue: key rotation policy not approved. Issue: UAT environment blocked by "
                            "whitelist approval. Risk: audit trail owner missing. Escalation required to IT "
                            "Director and Security Manager."
                        ),
                    },
                ],
            },
            "meeting_notes": [
                "Security manager said UAT should not proceed until key rotation policy is approved.",
                "Infra team cannot complete UAT environment provisioning because network whitelist approval is pending.",
                "No owner was named for final Network approval.",
                "Data Governance says AI usage audit trail owner must be assigned before governance sign-off.",
                "Decision needed: allow temporary manual key rotation for UAT or delay UAT entry.",
                "Action: PM to escalate policy and owner decisions to IT Director today.",
            ],
        },
    },
}
