# Phase 3 Architecture Cleanup Design

## Status
Proposed and approved for specification review.

## Context
Phase 1 and Phase 2 completed the requirement-workflow refactor:
- shared requirement workflow logic was centralized
- `ChatbotAgent` node responsibilities were extracted into focused helper modules
- `src/agent/agent_graph.py` now behaves much more like orchestration than a god object

The codebase is now in a healthier modular-monolith state, but several architectural pressure points remain:
- global `Config` coupling is still broad
- Jira and Confluence execution still depend on ad hoc MCP/direct-tool choices in the agent flow
- runtime and webapp concerns still share mutable process-wide state
- startup/composition concerns are spread across `app.py`, runtime helpers, and concrete services
- `sys.path.insert(...)` workarounds still exist in core modules

## Goals
- Introduce stable application-facing ports for Jira, Confluence, evaluation, and RAG ingestion.
- Move MCP-vs-direct fallback behavior behind adapters instead of keeping that policy in agent nodes.
- Centralize dependency construction in one composition layer.
- Reduce direct `Config` reach inside application logic.
- Clarify app-scoped versus request-scoped runtime ownership.
- Improve request execution safety and testability without changing the public API contract.

## Non-Goals
- No migration to microservices.
- No full package-wide Clean Architecture rewrite in one step.
- No product-level behavior changes for Jira, Confluence, MCP, RAG, or Coze beyond architectural cleanup.
- No database redesign or persistence-model rewrite in this phase.

## Target Architecture

### Composition / Runtime Layer
Primary ownership:
- startup wiring
- settings loading
- dependency assembly
- app/runtime object graph construction

Representative files:
- `app.py`
- `src/webapp/runtime.py`

This layer should construct dependencies and expose runtime access, but should not own workflow rules or transport fallback policy.

### Interface Layer
Primary ownership:
- Flask route entrypoints
- LangGraph node orchestration
- request/state mapping

Representative files:
- `src/agent/agent_graph.py`
- `src/webapp/routes/*`

This layer should orchestrate requests and state transitions, but should not construct tools directly or decide low-level MCP/direct transport policy.

### Application Layer
Primary ownership:
- business workflow sequencing
- stable use-case behavior
- partial-success policy
- normalized result objects

Representative files:
- `src/services/requirement_workflow_service.py`
- new Phase 3 application services where needed

This layer should depend on ports and plain data, not on Flask, MCP transport, or direct tool classes.

### Port / Adapter Boundary
Phase 3 introduces explicit ports and adapters.

Ports:
- `JiraIssuePort`
- `ConfluencePagePort`
- `JiraEvaluationPort`
- `RagIngestionPort`
- `ChatExecutionFactory` or equivalent request-safe session/execution port

Adapters:
- MCP Jira adapter
- direct Jira adapter
- fallback Jira adapter
- MCP Confluence adapter
- direct Confluence adapter
- fallback Confluence adapter
- RAG ingestion adapter

The key design decision is that fallback adapters own:
- MCP-first execution
- timeout/error detection
- direct-tool fallback
- result normalization into one stable internal result shape

### Infrastructure Layer
Primary ownership:
- MCP transport/client management
- direct external API calls
- auth/config plumbing
- concrete provider/tool implementations

Representative files:
- `src/mcp/mcp_integration.py`
- `src/mcp/mcp_client.py`
- `src/tools/jira_tool.py`
- `src/tools/confluence_tool.py`

## Proposed Package Direction
Phase 3 should evolve the repo toward this shape without a big-bang rewrite:

```text
src/
  application/
    ports/
      jira_issue_port.py
      confluence_page_port.py
      jira_evaluation_port.py
      rag_ingestion_port.py
      chat_execution_factory.py
    services/
      requirement_workflow_service.py
      agent_execution_service.py
  adapters/
    jira/
      mcp_jira_adapter.py
      direct_jira_adapter.py
      fallback_jira_adapter.py
    confluence/
      mcp_confluence_adapter.py
      direct_confluence_adapter.py
      fallback_confluence_adapter.py
    rag/
      rag_ingestion_adapter.py
  runtime/
    settings.py
    composition.py
  agent/
  webapp/
  mcp/
  tools/
  services/
```

Migration rule:
- introduce new packages gradually
- keep existing modules working during transition
- prefer extraction and wrapper adapters over file-moving churn

## Phase 3 Scope

### Phase 3a: Backend Architecture Cleanup
Goal:
- decouple agent/application logic from transport details

Scope:
- define ports and stable result DTOs for Jira, Confluence, evaluation, and RAG ingestion
- add fallback adapters that hide MCP-vs-direct behavior
- move Jira/Confluence execution policy out of `agent_graph.py`
- add a composition module that assembles concrete adapters and services
- reduce direct `Config` usage in application-facing logic
- remove `sys.path.insert(...)` workarounds where packaging cleanup is straightforward

Success criteria:
- `agent_graph.py` no longer owns Jira/Confluence fallback policy
- application services depend on ports, not concrete transport implementations
- Jira and Confluence execution both return stable normalized result shapes
- tests can mock ports cleanly without patching deep transport internals

### Phase 3b: Runtime / Webapp Cleanup
Goal:
- improve request isolation and runtime clarity

Scope:
- clarify app-scoped versus request-scoped objects
- reduce shared mutable chatbot/runtime state
- introduce a request-safe execution/session factory
- further narrow `app.py` responsibility to composition/bootstrap
- make runtime lookup and route dependencies more explicit and more testable

Success criteria:
- request execution no longer depends on broad mutable singleton behavior
- runtime initialization is explicit and easy to test
- route handlers rely on stable runtime/application services
- concurrency risk around chatbot execution is reduced materially

## Recommended Sequencing
1. Define ports and normalized result objects.
2. Implement Jira fallback adapters behind the new ports.
3. Implement Confluence fallback adapters behind the new ports.
4. Introduce composition wiring to assemble services and adapters in one place.
5. Switch `RequirementWorkflowService` and agent orchestration to depend on ports.
6. Introduce request-safe execution/session creation for runtime use.
7. Reduce global runtime mutation and simplify route/runtime ownership.
8. Remove obsolete wrappers and compatibility shims only after verification.

## Error Handling Strategy
- Preserve current user-facing success/failure message shapes where practical.
- Keep partial-success behavior:
  - Jira success with Confluence failure remains a partial success
  - MCP failure with direct fallback remains supported
- Move transport-specific timeout/auth/permission detection into adapters.
- Keep application services focused on workflow decisions, not protocol parsing.

## Testing Strategy

### Unit Tests
- ports and DTO behavior
- fallback adapters
- composition wiring smoke tests
- request-safe runtime/session factory behavior

### Integration Tests
- Jira adapter integration with MCP/direct fallback expectations
- Confluence adapter integration with MCP/direct fallback expectations
- agent integration verifying orchestration still produces current behavior
- runtime/route integration verifying request-scoped execution and service resolution

### Regression Guardrails
- preserve current agent smoke tests
- preserve current Coze integration tests
- preserve requirement workflow service tests
- add focused runtime concurrency-safety tests where feasible

## Risks
- introducing too many abstractions at once
- breaking MCP fallback behavior while "cleaning up"
- creating architecture that looks cleaner but is harder to debug
- coupling Phase 3a and Phase 3b too tightly and making the rollout too large

## Mitigations
- split implementation into Phase 3a then Phase 3b
- keep adapter boundaries narrow and concrete
- preserve current message/result behavior wherever possible
- use incremental extraction with passing tests after each slice
- defer cosmetic moves until after behavioral seams are stable

## Recommendation
Proceed with Phase 3 as one architecture initiative with two controlled implementation sub-phases:
- Phase 3a for backend ports/adapters/composition cleanup
- Phase 3b for runtime/webapp/request-isolation cleanup

This gives the best balance between architectural value, implementation safety, and forward momentum without turning the refactor into a full rewrite.
