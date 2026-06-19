# PM Status Agent

The PM Status Agent is a selectable agent mode for delivery governance. It turns Jira issues, Confluence project pages, and optional meeting notes into a structured PM status report.

## Inputs

- Project key, Jira key, milestone, sprint, or JQL-like scope in the user message.
- Confluence project context discovered through the configured read adapter.
- Optional pasted meeting notes under `Meeting notes:`.

## Output

- Health color: `Green`, `Amber`, or `Red`.
- Executive summary and stakeholder update.
- Progress, risks, blockers, decisions needed, owner gaps, and next actions.
- Source references for Jira issues and Confluence pages.
- Suggested Confluence status-page content.

## Human Approval

The agent never writes PM status content automatically. When Confluence write-back is available, it stores a pending confirmation state and shows `Approve` and `Cancel` quick actions.

- `approve` publishes only the pending Confluence status page draft.
- `cancel` clears pending state and performs no write operation.

## Runtime Mode

Use the web UI selector or send:

```json
{
  "message": "Generate PM status for AIP for the weekly review",
  "agent_mode": "pm_status_agent"
}
```

The mode is implemented through the existing Flask runtime and LangGraph flow, not a separate service.
