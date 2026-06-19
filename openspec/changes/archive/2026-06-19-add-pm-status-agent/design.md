## Context

The current product already has a Flask web UI, persistent conversations, explicit agent mode selection, LangGraph routing, Requirement SDLC Agent state, Jira/Confluence creation workflows, MCP fallback behavior, RAG ingestion/query boundaries, and workflow progress rendering. The PM Status Agent should reuse those foundations rather than introduce a separate service.

The main architectural gap is read-side Atlassian access. Existing Jira and Confluence ports are create-oriented. PM status generation needs to retrieve Jira issues by JQL/project context, inspect issue details and comments, retrieve Confluence pages, and merge those signals with optional meeting notes.

## Goals / Non-Goals

**Goals:**

- Add a PM Status Agent as a first-class agent mode alongside Auto and Requirement SDLC Agent.
- Generate a structured project status report from Jira, Confluence, and meeting-note signals.
- Keep write-back operations human-approved.
- Reuse existing LLM, MCP, RAG, memory, runtime, and UI workflow-progress foundations.
- Add read-side Jira and Confluence ports so PM status logic depends on application contracts instead of low-level tools.

**Non-Goals:**

- Do not replace the Requirement SDLC Agent.
- Do not automatically update Jira or Confluence without user approval.
- Do not build a separate PM Copilot service or frontend.
- Do not implement full portfolio, resource, or financial project management in the first version.
- Do not require all Jira/Confluence data to come through MCP; direct API fallback remains acceptable.

## Decisions

### Decision 1: Add PM Status Agent as an agent mode

The PM workflow will be exposed as `pm_status_agent` through the existing agent mode selector, HTTP request payload, runtime state, and LangGraph route.

Alternative considered: create a standalone service. This would duplicate auth, memory, UI, LLM routing, and Atlassian configuration. The existing platform is already the right host.

### Decision 2: Use read ports before PM reasoning

Add read-oriented application ports:

- `JiraProjectReadPort`
  - `search_issues(jql, max_results)`
  - `get_issue(issue_key)`
  - `get_issue_comments(issue_key)`
- `ConfluenceReadPort`
  - `get_page(page_id=None, title=None)`
  - `search_pages(query, space_key=None, limit=10)`

PM status services will consume these ports rather than calling `JiraTool`, `ConfluenceTool`, or `MCPIntegration` directly.

Alternative considered: let the PM Agent call arbitrary MCP tools directly. This is flexible but makes tests, fallback behavior, and auditability much weaker.

### Decision 3: Separate analysis from optional write-back

The first PM Status Agent turn generates a draft report and suggested actions. If write-back is requested, the agent enters a confirmation state and shows quick actions. Only after approval can it create a Confluence status page or draft Jira update recommendations.

Alternative considered: directly create status pages. That is too risky for enterprise PM workflows where status messages can affect stakeholder trust.

### Decision 4: Use a structured project status model

The service will normalize raw signals into a `ProjectStatusReport` containing:

- project key/name
- time window
- health color
- executive summary
- progress items
- risks/issues/blockers
- decisions needed
- owner and due-date gaps
- next actions
- suggested Jira updates
- suggested Confluence status page content
- stakeholder update draft
- source references

Alternative considered: return only Markdown. Markdown is useful for display, but a structured model is needed for tests, UI rendering, audit, and future write-back.

### Decision 5: Keep PM skill behavior inside prompts and service boundaries

The sub-skill concepts map to service responsibilities:

- jira/confluence-expert: read-side signal collection
- meeting-analyzer: meeting-note extraction
- senior-pm: health, risk, blocker, and decision judgment
- team-communications: stakeholder-ready output

They will be represented as prompt sections and service methods, not as runtime-installed external skills.

## Risks / Trade-offs

- Jira/Confluence read APIs may return incomplete or inconsistent data -> include source references and confidence notes in the report.
- MCP tool names may differ across deployments -> hide MCP selection behind read adapters and provide direct API fallbacks.
- PM health judgment may overstate risk -> require explicit rationale and preserve raw source references.
- Meeting notes may contain ambiguous commitments -> classify uncertain action items separately from confirmed actions.
- Agent mode list touches UI, API validation, runtime state, intent routing, and graph builder -> add targeted unit tests for each boundary.

## Migration Plan

1. Add PM status domain models and unit tests.
2. Add Jira and Confluence read ports with fake-backed tests.
3. Add direct API adapters and MCP fallback adapters for read-side behavior.
4. Add `ProjectStatusAgentService` with deterministic fake tests around report shape and human approval state.
5. Extend agent graph, intent service, chatbot runtime state, API validation, and frontend agent mode selector.
6. Add integration tests using fakes before enabling real Jira/Confluence calls.

Rollback is straightforward: remove `pm_status_agent` from the frontend selector/API validation and route unknown PM requests to general chat. Existing Requirement SDLC behavior remains unchanged.

## Open Questions

- Which Jira fields are mandatory for first-class PM status: sprint, fixVersion, due date, labels, components, assignee, reporter, status category, or custom milestone fields?
- Should the first write-back target be a Confluence status page, Jira comments, or both?
- Should PM status reports be stored in conversation metadata only, or also ingested into RAG for longitudinal project memory?
