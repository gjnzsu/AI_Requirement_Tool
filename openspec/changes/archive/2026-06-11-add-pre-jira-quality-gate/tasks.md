## 1. Settings and Test Fixtures

- [x] 1.1 Add unit tests for environment-backed quality settings defaults and overrides.
- [x] 1.2 Add `RequirementEvaluationSettings` or equivalent settings object covering deterministic gate, pre-Jira judge review, and post-Jira maturity evaluation.
- [x] 1.3 Wire new settings defaults into `config/config.py` without changing existing provider configuration behavior.
- [x] 1.4 Extend requirement workflow test fakes to capture Jira creation calls, judge calls, and post-Jira evaluation calls independently.

## 2. Deterministic Gate

- [x] 2.1 Add failing workflow tests proving missing acceptance criteria blocks Jira creation when the deterministic gate is enabled.
- [x] 2.2 Add failing workflow tests proving non-empty acceptance criteria allow Jira creation when the deterministic gate is enabled.
- [x] 2.3 Add failing workflow tests proving disabled deterministic gate preserves existing Jira creation behavior.
- [x] 2.4 Implement `RequirementGateService` with a narrow v1 acceptance-criteria readiness check.
- [x] 2.5 Wire deterministic gate execution before `RequirementWorkflowService.create_jira_issue()`.
- [x] 2.6 Surface blocked gate status in `workflow_progress` with downstream Jira, Confluence, and RAG steps skipped.

## 3. LLM Judge Review

- [x] 3.1 Add unit tests for a successful pre-Jira judge review returning structured advisory feedback.
- [x] 3.2 Add unit tests proving low judge scores do not block Jira creation when the deterministic gate passes.
- [x] 3.3 Add unit tests proving judge timeout, provider error, or invalid JSON does not block Jira creation when the deterministic gate passes.
- [x] 3.4 Implement `RequirementJudgeService` with a structured prompt and validated review payload.
- [x] 3.5 Add response formatting for concise judge feedback that distinguishes advisory findings from hard blockers.
- [x] 3.6 Wire judge review before Jira creation and after deterministic gate pass when judge review is enabled.

## 4. Preserve Post-Jira Maturity Evaluation

- [x] 4.1 Add regression tests proving existing post-Jira maturity evaluation still runs after successful Jira creation when enabled.
- [x] 4.2 Add tests proving post-Jira maturity evaluation can be disabled independently from deterministic gate and pre-Jira judge review.
- [x] 4.3 Preserve the existing `overall_maturity_score`, `detailed_scores`, `strengths`, `weaknesses`, and `recommendations` result shape.
- [x] 4.4 Keep Confluence and RAG ingestion behavior compatible with existing maturity evaluation payloads.

## 5. Workflow Result and UI Compatibility

- [x] 5.1 Decide whether pre-Jira judge output is a first-class `RequirementWorkflowResult` field or a structured response/progress detail.
- [x] 5.2 Update workflow response text to clearly label "Quality Review" separately from "Maturity Evaluation Results".
- [x] 5.3 Ensure existing web UI `workflow_progress` rendering handles blocked and advisory quality review details without layout changes.
- [x] 5.4 Add or update API/runtime tests if new workflow result fields are returned to the browser.

## 6. Verification and Documentation

- [x] 6.1 Run targeted requirement workflow unit tests.
- [x] 6.2 Run relevant runtime/API tests if response shape changes.
- [x] 6.3 Run `openspec validate add-pre-jira-quality-gate --strict`.
- [x] 6.4 Document the distinction between pre-Jira quality review and post-Jira maturity evaluation in the relevant feature or architecture docs.
