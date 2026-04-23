# Requirement SDLC Agentic Skill Repo Map

Use this reference when maintaining the Requirement SDLC Agent in this repository.

## Core Files

- `src/services/requirement_sdlc_agent_service.py`
  Owns the staged agent turn behavior: analysis, normalization, preview, confirmation, cancellation, revision, and approved workflow handoff.

- `src/services/requirement_workflow_service.py`
  Owns deterministic lifecycle execution: Jira creation, maturity evaluation, Confluence creation, RAG ingestion, and workflow progress.

- `src/agent/agent_graph.py`
  Composes the skill service, stores runtime state, exports workflow progress, and delegates graph node execution.

- `src/agent/graph_builder.py`
  Registers the `requirement_sdlc_agent` LangGraph node and route.

- `src/services/agent_intent_service.py`
  Selects `requirement_sdlc_agent` for explicit mode or active pending state.

- `src/services/intent_detector.py`
  Includes `requirement_sdlc_agent` as an LLM-detectable intent.

- `src/chatbot.py`
  Persists selected agent mode and `requirement_sdlc_agent_state` into conversation runtime state.

- `src/webapp/runtime.py`
  Snapshots/restores chatbot state, persists metadata, builds approval/cancel UI actions, and exports workflow progress.

## Important Identifiers

- Intent name: `requirement_sdlc_agent`
- Selected mode values: `auto`, `requirement_sdlc_agent`
- Conversation metadata key: `requirement_sdlc_agent_state`
- Workflow entry point: `RequirementWorkflowService.execute_backlog_data`
- Skill turn entry point: `RequirementSdlcAgentService.handle_turn`
- Progress export: `export_latest_requirement_workflow_progress`

## Existing Behavior To Preserve

- Explicit `agent_mode=requirement_sdlc_agent` must force routing to the skill.
- Pending `analysis` or `confirmation` state must route follow-up turns back to the skill.
- Approval must call `execute_backlog_data` exactly once for the approved draft.
- Cancellation must clear pending state and create nothing.
- Revision text during confirmation must return to analysis and preserve prior draft context.
- Malformed LLM JSON or unsafe draft payloads must fall back to a controlled clarification message.
- Durable actions must remain behind the approval gate.

## Focused Tests

- `tests/unit/test_requirement_sdlc_agent_service.py`
- `tests/unit/test_requirement_sdlc_agent_integration.py`
- `tests/unit/test_agent_intent_service.py`
- `tests/unit/test_agent_graph_builder.py`
- `tests/unit/test_webapp_runtime.py`
- `tests/unit/test_chatbot_requirement_workflow.py`
- `tests/unit/test_requirement_workflow_service.py`

## Common Pitfalls

- Do not put Jira/Confluence/RAG API logic into the skill service.
- Do not trust raw LLM draft fields without normalization.
- Do not lose pending state when the web runtime snapshots/restores the shared chatbot instance.
- Do not let general chat consume `approve` while confirmation is pending.
- Do not add a second prompt-only lifecycle implementation beside `RequirementWorkflowService`.
