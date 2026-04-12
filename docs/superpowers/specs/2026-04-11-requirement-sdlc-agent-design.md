# Requirement SDLC Agent Design

## Status
Proposed and approved in conversation for specification review.

## Context
The current chatbot architecture now has cleaner boundaries:
- requirement lifecycle execution is centralized in a shared workflow service
- general chat, RAG, Coze, intent routing, graph construction, Atlassian MCP support, and RAG ingestion each have focused modules or services
- `ChatbotAgent` is now much more of a coordinator than a monolith

This makes it practical to add a new product-facing specialist skill without duplicating backend logic.

The next product goal is a user-centric Requirement SDLC Agent that uses a Business Analyst interaction style during requirement analysis and quality assurance, while still executing through shared reusable workflow skills and the shared requirement workflow service.

## Goals
- Introduce a dedicated Requirement SDLC Agent as a product-facing specialist capability.
- Support both explicit selection and automatic routing from the same chatbot experience.
- Give the agent a Business Analyst-oriented interaction style for requirement analysis and quality assurance.
- Require a conversational confirmation step before executing durable actions.
- Reuse the shared requirement workflow service for Jira creation, evaluation, Confluence creation, and RAG ingestion.
- Preserve one source of truth for lifecycle execution logic.

## Non-Goals
- No migration of RAG to the external self-hosted service in this phase.
- No enterprise-wide BA scope such as stakeholder mapping, business process modeling, organizational change impact, or portfolio governance.
- No standalone new frontend flow outside the chatbot UI for the PoC.
- No second prompt-only execution agent that duplicates workflow logic.
- No partial step-by-step confirmation flow in the PoC.

## Product Summary
The Requirement SDLC Agent is a specialist conversational workflow capability that helps users transform rough ideas into high-quality software requirements before execution.

It should:
- interpret rough requirement ideas
- identify missing requirement-critical information
- improve clarity and testability
- surface assumptions and ambiguities
- present a structured draft preview
- ask for one final approval in chat
- run the full lifecycle after approval

It should not:
- behave like a generic enterprise BA consultant
- silently create Jira or Confluence content without approval
- reimplement backend execution rules in prompts

For the PoC, this skill should be implemented as a single specialist agent with internal stages, not as a multi-agent workflow.

## Skill Model

### Product Object
The product capability being built is the `Requirement SDLC Agent`.

It is important to distinguish this from a persona-only BA agent:
- the skill is the user-facing workflow capability
- the BA behavior is the reasoning style used during the analysis stage
- the shared workflow service remains the execution engine

This keeps the product centered on a reusable workflow, not on a prompt persona that would eventually need to reimplement execution logic.

### PoC Implementation Model
For the first stage, the Requirement SDLC Agent should be implemented as:
- one specialist agent
- one staged skill state machine
- internal stages instead of multiple collaborating agents

This implementation model is intentionally narrow for the PoC. It preserves a clean upgrade path to a future multi-agent design if the product later needs deeper specialization, but it avoids premature complexity now.

## User Experience

### Entry Modes
The Requirement SDLC Agent should be reachable in two ways:
- explicit selection by the user as a dedicated skill or agent mode
- automatic routing from the same chatbot conversation when the user request clearly looks like requirement lifecycle work

Examples:
- "Use the requirement lifecycle agent"
- "Help me turn this into a requirement"
- "Create a requirement for this feature"
- "Draft a ticket and docs for this idea"

### PoC Flow
1. User provides a rough requirement idea or feature description in the chatbot UI.
2. Routing selects the Requirement SDLC Agent.
3. The skill enters its intake stage and extracts known requirement fields from the message.
4. The skill enters its BA analysis stage and asks only the minimum missing questions needed for requirement quality.
5. The skill performs BA-style quality analysis on the draft.
6. The skill enters its preview stage and presents one consolidated draft in chat.
7. The user approves or asks for edits in chat.
8. After approval, the skill enters its execution stage and the shared workflow service runs:
   - create Jira
   - evaluate requirement quality/maturity
   - create Confluence
   - ingest to RAG
9. The skill enters its result stage and returns the final summary and links.

### Internal Stages
The PoC skill should use one specialist agent with these internal stages:
1. Intake
2. BA Analysis
3. Draft Preview
4. User Confirmation
5. Lifecycle Execution
6. Result Summary

This keeps the PoC simple while still making the product an agentic workflow skill rather than a single free-form chat persona.

### Confirmation Model
The PoC uses one full-package confirmation before execution.

Why:
- Jira and Confluence creation are durable and visible actions
- RAG ingestion propagates content into downstream retrieval
- one confirmation is enough for safety without adding too much friction

The skill should say something close to:

> I've prepared the requirement draft below. If you approve it, I'll create the Jira issue, evaluate the requirement, create the Confluence page, and ingest the result into RAG. Reply with `approve` to continue, or tell me what to change.

## BA Analysis Scope

### In Scope
The BA analysis stage should focus on requirement analysis and quality assurance for software/product requirement drafting.

It should improve:
- clarity
- business value framing
- acceptance criteria quality
- scope boundaries
- ambiguity detection
- assumption surfacing
- testability

### Out of Scope for the PoC
The BA analysis stage should not yet expand into:
- stakeholder workshops
- business process analysis
- organizational change management
- dependency mapping across large programs
- financial modeling
- portfolio prioritization frameworks

This keeps the PoC narrow enough to ship quickly while still delivering visible value.

## BA Prompt Design

### Prompt Role
The Requirement SDLC Agent should use a BA-flavored system prompt during its analysis and draft-refinement stages.

The BA prompt is an internal stage tool for the skill. It is not the definition of the product itself, and it must not become the source of truth for workflow execution behavior.

### BA Knowledge Prompt
Use a prompt along these lines:

> You are the Requirement SDLC Agent operating with a Business Analyst background.
> 
> Your job is to help users transform rough software or product ideas into clear, testable, execution-ready requirements.
> 
> You focus on requirement analysis and quality assurance. You are not a broad enterprise strategy consultant.
> 
> When working with a user:
> - extract what is already known from their message
> - identify only the missing information that materially blocks a high-quality requirement draft
> - ask the minimum number of follow-up questions needed
> - improve clarity, scope, business value, and acceptance criteria
> - distinguish clearly between user-provided facts, reasonable assumptions, and open questions
> - surface ambiguity, weak business value, and non-testable requirements
> - prefer concise structured drafts over verbose analysis
> 
> Before execution, review the draft for:
> - clarity
> - business value
> - acceptance criteria completeness
> - testability
> - ambiguous wording
> - hidden assumptions
> 
> Do not create Jira issues, Confluence pages, or trigger RAG ingestion until the user explicitly confirms.
> 
> When presenting a draft, provide:
> - Summary
> - Problem / Goal
> - Business Value
> - Scope Notes
> - Acceptance Criteria
> - Assumptions / Open Questions
> - Priority
> - Planned execution steps
> 
> Be concise, structured, and practical. The user should feel like they are working with a sharp Business Analyst who improves requirement quality without adding unnecessary ceremony.

### Prompt Design Rules
- The prompt shapes conversation quality, not execution logic.
- The prompt must not become the source of truth for Jira, Confluence, or RAG behavior.
- The prompt must produce structured outputs that can feed the workflow service cleanly.

## Draft Model

### Draft Content
The Requirement SDLC Agent should maintain a structured draft that includes:
- summary
- problem_goal
- business_value
- scope_notes
- acceptance_criteria
- assumptions
- open_questions
- priority
- execution_plan

### Preview Shape
The preview shown to the user in chat should include:
- Summary
- Problem / Goal
- Business Value
- Acceptance Criteria
- Assumptions / Open Questions
- Priority
- Planned Actions: create Jira, evaluate requirement, create Confluence, ingest to RAG

This should be detailed enough for user review, but still compact enough to fit naturally into chat.

## Architecture

### Top-Level Model
The target product structure is:
- General Chat Agent
- Coze Agent
- Requirement SDLC Agent

The chatbot remains the shared interaction surface and top-level router.

### Recommended Backend Shape
- `ChatbotAgent` remains the top-level coordinator and router.
- A new `RequirementSdlcAgentService` or equivalent owns the staged agent behavior and internal workflow-skill orchestration:
  - staged skill progression
  - BA-style intake and analysis
  - draft creation and update
  - confirmation handling
  - deciding when execution can start
- `RequirementWorkflowService` remains the execution source of truth.
- existing adapters and helper services remain responsible for external integrations.

### Key Rule
The Requirement SDLC Agent should be a staged conversational facade over shared workflow skills and the shared workflow service, not a second implementation of the lifecycle.

That means:
- stage orchestration belongs in the skill service
- BA-style reasoning belongs in the specialist prompt/analysis stage
- deterministic execution belongs in the workflow service
- transport/integration behavior belongs in ports/adapters/helpers

### PoC Structure Choice
For the first stage, the skill should be implemented as:
- one specialist agent
- one skill state machine
- internal stages instead of multiple collaborating agents

Why:
- lower implementation complexity
- easier debugging in the existing chatbot runtime
- cleaner reuse of the shared workflow service
- a better foundation before adding any future multi-agent decomposition

## State Model

### Pending Draft State
The PoC needs request- or session-scoped pending draft state so the agent can pause for approval.

Suggested state fields:
- `active_specialist_agent`
- `pending_requirement_draft`
- `pending_confirmation_required`
- `pending_execution_scope`
- `last_draft_revision`

### Confirmation Detection
The next user message after the preview should be interpreted as one of:
- approval
- revision request
- cancellation
- unrelated input

Approval examples:
- `approve`
- `yes`
- `go ahead`
- `proceed`

Revision examples:
- `change the priority to High`
- `add audit logging to the acceptance criteria`
- `make it narrower`

Cancellation examples:
- `cancel`
- `stop`
- `do not create anything`

## Routing Design

### Explicit Routing
If the user explicitly selects or names the Requirement SDLC Agent, routing should prefer it.

### Automatic Routing
If the user request clearly resembles requirement drafting or requirement lifecycle work, routing should select the Requirement SDLC Agent instead of general chat or Coze.

Routing examples:
- requirement drafting requests -> Requirement SDLC Agent
- AI news / report / Coze-specific tasks -> Coze Agent
- normal conversational requests -> General Chat

### Confirmation-Aware Routing
If a pending requirement draft exists and the staged SDLC flow is still active, follow-up user input should route back to the Requirement SDLC Agent until the draft is approved, edited, or cancelled.

## Execution Contract

### Before Approval
The Requirement SDLC Agent should not directly implement durable side effects.

It may:
- analyze the user input
- produce a structured draft
- revise the draft
- explain quality concerns

### After Approval
The Requirement SDLC Agent should call internal workflow skills backed by the existing shared workflow service for the full lifecycle package:
- Jira creation
- evaluation
- Confluence creation
- RAG ingestion

The execution path must remain the same backend source of truth used elsewhere.

## Error Handling
- If draft quality is too weak, the agent should ask clarifying questions instead of executing.
- If the user does not approve, execution must not begin.
- If execution partially succeeds, the agent should return a clear partial-success summary.
- If execution fails, the agent should preserve draft context so the user can retry or revise.

## Testing Strategy

### Unit Tests
- skill stage transitions
- BA draft extraction and revision behavior
- confirmation state transitions
- approval / edit / cancel detection
- routing into the Requirement SDLC Agent
- integration from the skill service to the shared workflow service

### Integration Tests
- end-to-end conversational draft -> approval -> execution flow
- explicit skill selection
- automatic routing into the Requirement SDLC Agent
- partial-success behavior after approval

## PoC Rollout Recommendation
Implement the PoC in this order:
1. introduce specialist-agent routing support
2. add pending draft state and confirmation handling
3. add BA draft generation and preview formatting
4. connect approval to the shared workflow service
5. add tests for approval, revision, and cancellation flows

## Risks
- accidentally duplicating workflow logic in prompts
- over-expanding the BA analysis stage into a generic enterprise analyst experience
- losing draft state across confirmation turns
- making the confirmation UX too verbose for chat

## Mitigations
- keep execution in the shared workflow service
- keep BA scope narrow in the PoC
- use compact structured previews
- add clear pending-draft state handling and tests

## Recommendation
Proceed with a PoC Requirement SDLC Agent using Approach 2:
- a single specialist agent with internal stages
- BA-guided analysis and quality assurance
- explicit and automatic routing support
- one in-chat approval checkpoint
- shared backend execution through the existing requirement workflow service

This gives the clearest path to a productized agentic workflow skill without reintroducing monolithic agent logic or duplicating execution behavior.

