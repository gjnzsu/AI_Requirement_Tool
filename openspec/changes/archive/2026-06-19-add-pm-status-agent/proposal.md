## Why

The product already supports requirement analysis, Jira creation, Confluence documentation, RAG, MCP, and guided human-approved workflows. A PM Agent can extend that same platform from requirement intake into delivery governance by turning Jira, Confluence, and meeting signals into project health, risks, decisions, and stakeholder-ready communication.

This is valuable now because the current architecture has the agent, UI, memory, MCP, and workflow-progress foundations needed for a focused PM status workflow without creating a separate service.

## What Changes

- Add a new PM Status Agent mode that produces project status reports from project keys, sprint or milestone context, Confluence pages, and optional meeting notes.
- Add read-side Jira and Confluence capability boundaries for project status analysis.
- Add a structured PM status report model covering health color, progress, risks, blockers, decisions, owner gaps, next actions, and stakeholder update drafts.
- Add a human-approved workflow for optional write-back suggestions, such as Confluence status-page drafts or Jira update recommendations.
- Extend agent routing and UI agent-mode selection to support the PM Status Agent.
- Preserve existing Requirement SDLC Agent behavior.

## Capabilities

### New Capabilities

- `pm-status-agent`: Generate PM project status analysis and stakeholder-ready updates from Jira, Confluence, and meeting-note inputs with human approval before write-back.

### Modified Capabilities

- None.

## Impact

- Agent graph: add a `pm_status_agent` route and handler alongside `requirement_sdlc_agent`.
- Intent/routing: add keyword and explicit agent-mode support for PM status requests.
- Runtime/UI: add PM Status Agent as an allowed `agent_mode` and selectable frontend option.
- Application services: add PM status orchestration service and project status report model.
- Jira/Confluence integration: add read-oriented ports/adapters for Jira JQL issue retrieval and Confluence page lookup/search.
- Tests: add unit coverage for routing, graph execution, PM status generation, and read-port behavior with fakes.
