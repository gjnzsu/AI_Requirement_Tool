# PM Status Agent Test Data

This folder contains contract-level test fixtures for the `pm_status_agent` change.

Use these fixtures in three ways:

1. Manual prompt testing before implementation.
2. Unit-test fixtures for `ProjectStatusWorkflowService` and `ProjectStatusAgentService`.
3. Golden-output checks for PM judgment and stakeholder communication formatting.

## Scenarios

| Fixture | Expected health | Purpose |
|---|---:|---|
| `scenario-01-on-track.json` | Green | Delivery is progressing normally with no material blockers. |
| `scenario-02-delayed-no-blocker.json` | Amber | Delivery is delayed, but there is no active blocker and recovery is plausible. |
| `scenario-03-delayed-with-blocker.json` | Red | Delivery is delayed and blocked by unresolved dependency or decision. |

## Suggested Manual Test Prompt

Paste one fixture's `input` object into the PM Status Agent and ask:

```text
Generate a PM status report for this project.
Classify health as Green, Amber, or Red.
Return executive summary, progress, risks/issues/blockers, decisions needed,
next actions, suggested Jira updates, suggested Confluence status-page content,
and stakeholder update draft.
```

## Acceptance Checks

For every fixture, verify:

- Health color matches `expected.health`.
- PM judgment uses evidence from Jira, Confluence, and meeting notes.
- Output distinguishes risks from blockers.
- Output includes owners and due dates when available.
- Output flags missing owners or dates.
- Output suggests write-back actions but does not claim to perform them.

