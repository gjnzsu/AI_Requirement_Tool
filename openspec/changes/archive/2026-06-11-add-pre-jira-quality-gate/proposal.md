## Why

The current requirement evaluation happens after Jira issue creation, so it produces a maturity report after the durable workflow action has already occurred. This limits its product value because users need quality feedback before approval and Jira creation, when they can still revise the draft.

This change adds a pre-Jira requirement quality gate that combines deterministic checks with an LLM-as-a-Judge advisory review, while preserving the existing post-Jira maturity evaluation for reporting, Confluence enrichment, and RAG ingestion.

## What Changes

- Add a pre-Jira deterministic gate for hard requirement readiness checks, starting with missing acceptance criteria.
- Add a pre-Jira LLM judge review that scores and explains requirement quality before Jira creation.
- Keep LLM judge findings advisory by default so the model does not become the sole hard blocker.
- Surface quality gate and judge outcomes through the existing requirement workflow response and workflow progress structure.
- Add environment-backed settings to enable or disable deterministic gate behavior and LLM judge review independently.
- Preserve the existing post-Jira maturity evaluator and its `overall_maturity_score` output shape.

## Capabilities

### New Capabilities

- `requirement-quality-gate`: Pre-Jira requirement quality checks and LLM judge review for approved requirement drafts.

### Modified Capabilities

- None.

## Impact

- `src/services/requirement_workflow_service.py`: run pre-Jira checks before Jira creation and include quality review output in workflow responses.
- `src/services/jira_maturity_evaluator.py`: remains post-Jira evaluation; no replacement in this change.
- New services for quality gate settings, deterministic gate evaluation, and LLM judge review.
- Tests around requirement workflow behavior, gate blocking, advisory judge output, and configuration.
- Optional web UI impact through existing `workflow_progress` rendering if new statuses or details are surfaced.
