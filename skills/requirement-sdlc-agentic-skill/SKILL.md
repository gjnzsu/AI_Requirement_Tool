---
name: requirement-sdlc-agentic-skill
description: Use when turning rough software or product ideas into SDLC-ready requirements through a stateful, human-in-the-loop agentic workflow. Applies to requirement intake, BA-style clarification, structured requirement drafting, revision, approval gating, Jira issue creation, maturity evaluation, Confluence documentation, RAG ingestion, workflow progress reporting, or maintaining the Requirement SDLC Agent implementation.
---

# Requirement SDLC Agentic Skill

## Purpose

Use this skill to operate or extend a Requirement SDLC Agent that converts rough ideas into execution-ready requirement artifacts. Treat it as a supervised agentic workflow: reason over user input and context, maintain draft state, ask only material follow-up questions, wait for explicit approval, then coordinate durable lifecycle actions.

Keep the skill centered on requirement lifecycle work, not generic business analysis. The agent should improve clarity, business value, scope, acceptance criteria, assumptions, and testability.

## Agent Contract

The skill owns:

- Intake and interpretation of rough requirement ideas.
- BA-style analysis and quality checks.
- Structured draft creation and revision.
- Confirmation state and approval/cancel handling.
- Handoff to lifecycle execution services after approval.
- User-facing workflow progress and result summaries.

The skill must not own:

- Direct Jira, Confluence, or RAG integration logic.
- Durable side effects before explicit approval.
- Broad enterprise BA consulting outside software/product requirement quality.
- Duplicate implementations of existing workflow services.

## Core Workflow

1. Detect whether the user wants requirement lifecycle help.
2. Read recent conversation context and any pending requirement draft state.
3. Extract known facts into a structured draft.
4. Decide whether the draft is ready or materially underspecified.
5. Ask concise follow-up questions when information blocks a usable draft.
6. Present a compact preview when ready for confirmation.
7. Interpret the next user turn as approval, cancellation, or revision.
8. On approval only, execute the lifecycle workflow through the shared service.
9. Return a result summary with created artifacts, links, failures, and workflow progress.

## Draft Shape

Maintain a structured draft with these fields:

- `summary`
- `problem_goal`
- `business_value`
- `scope_notes`
- `acceptance_criteria`
- `assumptions`
- `open_questions`
- `priority`
- `invest_analysis`
- `description`

Build `description` from the normalized draft so downstream Jira creation has a deterministic payload.

## State Model

Use conversation-scoped state so approval and revision turns route back to this skill.

Expected state fields:

- `stage`: usually `analysis` or `confirmation`
- `awaiting_confirmation`: boolean
- `draft`: normalized draft payload
- `open_questions`: active clarification questions, when any
- `revision_request`: latest user revision text, when applicable

If `awaiting_confirmation` is true, keep routing follow-up messages to this skill until the user approves, cancels, or completes a revision.

## Approval Rules

Accept approval only from clear confirmation text such as:

- `approve`
- `approved`
- `yes`
- `go ahead`
- `proceed`

Accept cancellation from clear stop text such as:

- `cancel`
- `stop`
- `abort`
- `never mind`
- `do not create anything`
- `don't create anything`

Treat all other confirmation-stage input as a revision request. Re-analyze the draft using the previous state plus the user's revision.

## Execution Rules

Before approval, only analyze, ask, draft, and revise.

After approval, call the shared lifecycle workflow service using the approved draft. Expected execution steps are:

- Create Jira issue.
- Evaluate requirement maturity or quality.
- Create Confluence page when configured.
- Ingest the resulting page or summary into RAG when configured.
- Return workflow progress for UI display.

If a configured integration is missing or fails, report the partial outcome clearly and preserve enough context for retry or revision.

## Response Guidelines

Keep responses structured and short enough for chat.

For clarification:

- Ask only questions that materially affect requirement quality.
- Prefer one compact question set over a long interview.
- Preserve useful partial draft state.

For preview:

- Show Summary, Problem / Goal, Business Value, Scope Notes, Priority, Acceptance Criteria, Assumptions, Open Questions, and planned execution.
- End with an explicit instruction to approve, cancel, or request changes.

For completion:

- Report created Jira key and link.
- Report evaluation score or failure reason.
- Report Confluence link or configuration/failure reason.
- Report RAG ingestion status when available.

## Implementation Guidance

Keep orchestration and execution separated.

- Top-level agent/router: detect intent and route into this skill.
- Requirement SDLC skill service: own stages, draft state, confirmation, and handoff.
- Workflow service: own Jira, evaluation, Confluence, and RAG lifecycle execution.
- Adapters/tools: own external service protocols and fallbacks.
- Web/API runtime: persist conversation state and expose approval/progress UI actions.

For this repository, read `references/repo-implementation-map.md` when modifying the current implementation.

## Verification

For changes to this skill or its implementation, run focused tests for:

- Draft preview and clarification behavior.
- Approval, cancellation, and revision handling.
- Pending-state persistence.
- Intent routing back to the skill during confirmation.
- Lifecycle execution handoff.
- Workflow progress export.

In this repository, a useful focused command is:

```powershell
pytest tests\unit\test_requirement_sdlc_agent_service.py tests\unit\test_requirement_sdlc_agent_integration.py tests\unit\test_agent_intent_service.py tests\unit\test_agent_graph_builder.py tests\unit\test_webapp_runtime.py -q
```
