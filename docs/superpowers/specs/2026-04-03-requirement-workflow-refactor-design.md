# AI Requirement Workflow Refactor Design

## Status
Approved for implementation.

## Context
The current AI requirement assistant flow is split across large orchestration classes:
- `src/chatbot.py` owns direct Jira/Confluence workflow logic.
- `src/agent/agent_graph.py` owns a second implementation of similar Jira/Confluence behavior plus graph orchestration.

This creates duplicated business logic, large files, weak test seams, and higher regression risk when changing requirement-generation behavior.

## Goals
- Extract Jira issue creation, maturity evaluation, Confluence page generation, and user-facing workflow response formatting into one reusable application service.
- Refactor `Chatbot` and `ChatbotAgent` so they call the shared workflow service instead of each owning separate implementations.
- Split `ChatbotAgent` by node responsibility after the workflow service is in place.
- Preserve current runtime behavior and public API responses as much as possible during this first refactor.

## Non-Goals
- No migration to microservices in this slice.
- No redesign of the Flask API contract.
- No change to the RAG, MCP, or Coze product behavior beyond internal delegation cleanup unless needed to preserve compatibility.
- No broad package-wide Clean Architecture rewrite in this slice.

## Proposed Design

### Phase 1: Shared Requirement Workflow Service
Create `src/services/requirement_workflow_service.py` as the central application service for the AI requirement workflow.

Responsibilities:
- Build a backlog-generation prompt from the current user request and conversation context.
- Generate structured backlog data with the active LLM provider.
- Create the Jira issue through an injected Jira tool.
- Run Jira maturity evaluation through an injected evaluator when available.
- Build Confluence content and create a page through an injected Confluence tool when available.
- Format the final user-facing workflow response in one place.

Expected service shape:
- Constructor receives dependencies such as `jira_tool`, `confluence_tool`, `jira_evaluator`, and an LLM response callable/provider.
- One high-level method executes the end-to-end requirement workflow and returns a structured result plus a rendered response string.

`Chatbot._handle_jira_creation()` should become a thin adapter around this service.

`ChatbotAgent` Jira node(s) should delegate the shared business flow to this service while keeping MCP-specific fallback and graph-state updates in the agent layer.

### Phase 2: Split Agent Node Implementations
After Phase 1 reduces duplicated Jira/Confluence logic, split `src/agent/agent_graph.py` into smaller modules:
- intent detection module
- Jira/requirement workflow node module
- RAG node module
- Coze node module
- graph assembly/state module

`agent_graph.py` should mainly define state, wire nodes, and expose `ChatbotAgent.invoke()`.

## Dependency Direction
- `src/services/requirement_workflow_service.py` should depend on injected tool/evaluator/provider abstractions and plain data, not Flask or route-layer objects.
- `Chatbot` and `ChatbotAgent` depend on the workflow service.
- Flask route handlers continue depending on `Chatbot`, not on low-level Jira/Confluence workflow internals.

## Error Handling
- If backlog generation fails or returns malformed JSON, return a user-safe workflow error and log details.
- If Jira creation fails, return a failed workflow response without attempting Confluence creation.
- If maturity evaluation or Confluence creation fails after Jira creation succeeds, preserve partial success and include a user-facing warning in the response.
- Keep fallback behavior where MCP-specific calls fail but direct tool calls are still available.

## Testing Strategy
- Add unit tests for the workflow service covering:
  - successful Jira + evaluation + Confluence flow
  - Jira creation failure
  - malformed LLM JSON
  - Confluence failure after Jira success
- Add regression tests that `Chatbot._handle_jira_creation()` delegates correctly and preserves response shape.
- After Phase 2, add focused tests for extracted agent node modules and graph routing.

## Implementation Order
1. Introduce the shared workflow service and unit tests.
2. Refactor `Chatbot` to delegate Jira workflow handling.
3. Refactor `ChatbotAgent` Jira/Confluence node paths to reuse the service where behavior overlaps.
4. Split `agent_graph.py` into node modules once shared workflow logic is centralized.
5. Run targeted unit/integration tests after each phase.

## Risks and Mitigations
- Risk: response text changes break UI/user expectations.
  - Mitigation: preserve current formatting in the service and add regression tests.
- Risk: MCP-specific behavior is accidentally flattened into direct-tool behavior.
  - Mitigation: keep protocol/fallback concerns in agent/MCP layers and move only shared business formatting/execution into the service.
- Risk: one refactor slice becomes too large.
  - Mitigation: land Phase 1 first, verify tests, then do Phase 2 extraction module by module.
