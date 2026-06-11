## Context

The current requirement workflow creates a Jira issue first, then uses `JiraMaturityEvaluator` through `JiraEvaluationAdapter` to evaluate the created issue. That evaluator is already LLM-backed and useful for post-create reporting, Confluence enrichment, and RAG ingestion, but it does not help users improve the approved draft before durable Jira creation.

The Requirement SDLC Agent already owns conversational intake, draft preview, and explicit approval. `RequirementWorkflowService` owns the durable lifecycle execution after approval. The quality gate belongs in the workflow layer because it protects durable side effects regardless of whether execution was triggered by the SDLC agent or a legacy direct workflow path.

## Goals / Non-Goals

**Goals:**

- Add a pre-Jira deterministic gate for narrow, predictable hard blockers.
- Add a pre-Jira LLM-as-a-Judge review for semantic quality feedback.
- Keep judge findings advisory by default so users are not blocked solely by model judgment.
- Keep the existing post-Jira maturity evaluation in place and preserve its result shape.
- Make evaluation/gate behavior configurable through environment-backed settings.
- Surface quality outcomes through workflow progress and response text.

**Non-Goals:**

- Replace `JiraMaturityEvaluator` in this change.
- Add autonomous backlog rewriting without user approval.
- Add a new standalone UI workflow outside the existing chat UI.
- Persist judge scores to Jira custom fields.
- Block Jira creation based only on LLM judge scores in v1.

## Decisions

### Decision 1: Keep deterministic gate and LLM judge separate

The implementation will introduce a deterministic `RequirementGateService` and a separate `RequirementJudgeService`.

The deterministic gate handles objective checks such as missing acceptance criteria. The judge handles semantic review such as clarity, testability, ambiguity, and scope readiness.

Alternative considered: make the LLM judge the quality gate. This was rejected for v1 because LLM scoring can be subjective and should not be the only source of hard blocking for durable workflow actions.

### Decision 2: Run quality checks before Jira creation in `RequirementWorkflowService`

The pre-Jira checks will run inside `RequirementWorkflowService.execute_backlog_data()` before `create_jira_issue()`.

This keeps the check close to the durable side effect and protects all callers that delegate approved backlog data to the shared workflow service.

Alternative considered: run the gate only in `RequirementSdlcAgentService` before confirmation. This was rejected because legacy or direct workflow callers could bypass the protection.

### Decision 3: Preserve post-Jira maturity evaluation

The existing `JiraMaturityEvaluator` remains responsible for evaluating created Jira issues. It will continue returning `overall_maturity_score`, `detailed_scores`, `strengths`, `weaknesses`, and `recommendations`.

The new judge review will produce a draft-focused review payload. The workflow may format both outputs, but they represent different phases:

- pre-Jira draft quality review
- post-Jira maturity evaluation

Alternative considered: replace the maturity evaluator with the new judge. This was rejected because Confluence/RAG/test code already depends on the post-Jira evaluator shape and because the two evaluations happen at different workflow moments.

### Decision 4: Use advisory judge output by default

The judge review will not block Jira creation in v1 unless configuration explicitly adds future blocking rules. It will be shown as actionable feedback and included in workflow progress detail.

Alternative considered: block when judge score falls below a threshold. This was rejected for v1 because threshold tuning needs product validation and may feel arbitrary to users.

### Decision 5: Use explicit settings

Add settings similar to:

- `REQUIREMENT_EVALUATION_ENABLED`
- `REQUIREMENT_EVALUATION_GATE_ENABLED`
- `REQUIREMENT_JUDGE_ENABLED`

The defaults should preserve existing behavior as much as practical while allowing teams to enable the new quality gate deliberately.

## Risks / Trade-offs

- LLM judge output may be inconsistent across providers -> Use structured JSON output, validation, conservative defaults, and advisory behavior.
- Adding pre-Jira review may increase latency -> Allow judge review to be disabled independently from deterministic gate checks.
- Users may confuse pre-Jira judge score with post-Jira maturity score -> Use distinct labels in response text and data structures.
- Deterministic gate could block valid edge cases -> Keep v1 hard blockers narrow and configurable.
- Existing tests assume evaluation runs after Jira creation -> Add targeted tests for both old and new paths rather than rewriting the evaluation stack.

## Migration Plan

1. Add configuration and settings objects with defaults.
2. Add deterministic gate service and wire it before Jira creation.
3. Add LLM judge service and output formatting without changing Jira creation behavior.
4. Preserve post-Jira evaluation flow and existing output shape.
5. Extend unit tests for gate blocking, judge advisory output, disabled settings, and existing post-Jira evaluation.
6. Document the distinction between pre-Jira review and post-Jira maturity evaluation.

Rollback is straightforward: disable the gate and judge settings, or remove the pre-Jira service wiring while leaving the existing post-Jira evaluator unchanged.

## Open Questions

- Should `REQUIREMENT_EVALUATION_GATE_ENABLED` default to false for safer rollout, or true because missing acceptance criteria is already a strong deterministic blocker?
- Should judge output be stored in `RequirementWorkflowResult` as a first-class field or embedded into `evaluation_result` with a phase marker?
- Should the UI render a separate "Quality Review" card, or is response text plus workflow progress enough for v1?
