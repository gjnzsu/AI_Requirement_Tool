## 1. Domain Model and Contracts

- [x] 1.1 Add PM status report dataclasses or typed models for health color, source references, progress, risks, blockers, decisions, owner gaps, next actions, suggested Jira updates, suggested Confluence page content, and stakeholder update draft.
- [x] 1.2 Add unit tests for PM status model normalization and serialization.
- [x] 1.3 Add `JiraProjectReadPort` with `search_issues`, `get_issue`, and `get_issue_comments` contract methods.
- [x] 1.4 Add `ConfluenceReadPort` with `get_page` and `search_pages` contract methods.

## 2. Jira and Confluence Read Adapters

- [x] 2.1 Implement direct Jira read adapter using existing Jira credentials and JQL support.
- [x] 2.2 Implement MCP-backed Jira read adapter or fallback wrapper where matching MCP tools are available.
- [x] 2.3 Implement direct Confluence read adapter for page lookup and search.
- [x] 2.4 Extend existing Confluence MCP helper behavior into a `ConfluenceReadPort` adapter.
- [x] 2.5 Add fake-backed unit tests for read adapters without requiring real Atlassian credentials.

## 3. PM Status Agent Services

- [x] 3.1 Add `ProjectStatusAgentService` that handles one PM Agent turn and returns report drafts, confirmation prompts, or completed write-back results.
- [x] 3.2 Add `ProjectStatusWorkflowService` that collects Jira, Confluence, and meeting-note signals through read ports.
- [x] 3.3 Add meeting-note extraction logic for actions, risks, decisions, owner references, and uncertain commitments.
- [x] 3.4 Add PM judgment prompt/service logic that produces Green, Amber, or Red with explicit rationale and source references.
- [x] 3.5 Add stakeholder communication rendering for daily status, RAID-style summary, and Confluence status-page draft.
- [x] 3.6 Add unit tests for PM report generation with fake Jira, Confluence, and meeting-note inputs.

## 4. Agent Graph and Routing Integration

- [x] 4.1 Extend agent state to hold PM status agent state and latest PM workflow progress.
- [x] 4.2 Extend `build_agent_graph` with a `pm_status_agent` node and route to END after PM handling.
- [x] 4.3 Extend keyword and LLM intent routing to detect PM status requests.
- [x] 4.4 Extend selected agent mode handling to accept `pm_status_agent`.
- [x] 4.5 Add unit tests for PM status explicit mode, keyword routing, pending PM confirmation state, and graph node execution.

## 5. Runtime, API, and UI Integration

- [x] 5.1 Extend `/api/chat` agent mode validation to allow `pm_status_agent`.
- [x] 5.2 Extend runtime state export/import to preserve pending PM status confirmation state per conversation.
- [x] 5.3 Extend UI agent mode selector with PM Status Agent.
- [x] 5.4 Extend UI notification text so PM Status Agent selection displays correctly.
- [x] 5.5 Extend workflow-progress rendering labels to support PM status progress.
- [x] 5.6 Add API and frontend-focused tests for PM Status Agent mode selection where current test patterns allow.

## 6. Human Approval and Write Back

- [x] 6.1 Add quick actions for approving or cancelling PM status write-back suggestions.
- [x] 6.2 Implement approved Confluence status-page creation through existing Confluence page creation capability.
- [x] 6.3 Return artifact links after approved write-back.
- [x] 6.4 Ensure cancellation performs no Jira or Confluence write operation.
- [x] 6.5 Add tests proving PM write-back is not executed before approval.

## 7. Documentation and Verification

- [x] 7.1 Update README agent mode documentation with PM Status Agent usage examples.
- [x] 7.2 Add docs describing expected PM Status Agent input patterns and output structure.
- [x] 7.3 Run focused unit tests for PM Agent routing, services, and adapters.
- [x] 7.4 Run the repository quality command or the closest available unit-test suite before marking the change complete.
