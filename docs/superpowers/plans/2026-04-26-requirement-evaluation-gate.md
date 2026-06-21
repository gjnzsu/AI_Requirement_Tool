# Requirement Evaluation Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add env-controlled requirement evaluation and a deterministic pre-Jira gate that blocks only when acceptance criteria are missing.

**Architecture:** Keep the Requirement SDLC agent conversational and unchanged in responsibility, and add the new behavior in the workflow layer. `RequirementWorkflowService` will resolve env-backed settings, run a deterministic gate before Jira creation, optionally run advisory evaluation, and then continue with Jira, Confluence, and RAG exactly as today when not blocked.

**Tech Stack:** Python, dataclasses, pytest, existing workflow service, existing config module, existing Jira evaluation integration.

---

### Task 1: Add Env-Backed Evaluation Settings

**Files:**
- Create: `src/services/requirement_evaluation_settings.py`
- Modify: `config/config.py`
- Test: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write the failing settings-resolution test**

```python
from config.config import Config
from src.services.requirement_evaluation_settings import RequirementEvaluationSettings


def test_requirement_evaluation_settings_defaults(monkeypatch):
    monkeypatch.setenv("REQUIREMENT_EVALUATION_ENABLED", "true")
    monkeypatch.setenv("REQUIREMENT_EVALUATION_GATE_ENABLED", "false")

    settings = RequirementEvaluationSettings.from_config(Config)

    assert settings.evaluation_enabled is True
    assert settings.gate_enabled is False
```

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: FAIL because `RequirementEvaluationSettings` does not exist yet.

- [ ] **Step 3: Add config flags and the settings dataclass**

```python
# config/config.py
REQUIREMENT_EVALUATION_ENABLED: bool = os.getenv(
    "REQUIREMENT_EVALUATION_ENABLED", "true"
).lower() in ("true", "1", "yes")
REQUIREMENT_EVALUATION_GATE_ENABLED: bool = os.getenv(
    "REQUIREMENT_EVALUATION_GATE_ENABLED", "false"
).lower() in ("true", "1", "yes")
```

```python
# src/services/requirement_evaluation_settings.py
from dataclasses import dataclass


@dataclass(frozen=True)
class RequirementEvaluationSettings:
    evaluation_enabled: bool = True
    gate_enabled: bool = False

    @classmethod
    def from_config(cls, config):
        return cls(
            evaluation_enabled=getattr(config, "REQUIREMENT_EVALUATION_ENABLED", True),
            gate_enabled=getattr(config, "REQUIREMENT_EVALUATION_GATE_ENABLED", False),
        )
```

- [ ] **Step 4: Run the targeted test and verify it passes**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: PASS for the settings assertions and existing workflow tests still passing.

- [ ] **Step 5: Commit**

```bash
git add config/config.py src/services/requirement_evaluation_settings.py tests/unit/test_requirement_workflow_service.py
git commit -m "feat: add env-backed requirement evaluation settings"
```

### Task 2: Add Deterministic Acceptance-Criteria Gate

**Files:**
- Create: `src/services/requirement_gate_service.py`
- Modify: `src/services/requirement_workflow_service.py`
- Test: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write failing tests for blocking and non-blocking gate behavior**

```python
def test_execute_backlog_data_blocks_when_gate_enabled_and_acceptance_criteria_missing():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        evaluation_settings=RequirementEvaluationSettings(
            evaluation_enabled=True,
            gate_enabled=True,
        ),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": [],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is False
    assert "acceptance criteria are missing" in result.response_text.lower()
    assert result.workflow_progress[0]["status"] == "skipped"
    assert result.workflow_progress[1]["status"] in {"failed", "blocked"}


def test_execute_backlog_data_allows_creation_when_gate_enabled_and_acceptance_criteria_present():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        evaluation_settings=RequirementEvaluationSettings(
            evaluation_enabled=True,
            gate_enabled=True,
        ),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert result.jira_result["key"] == "PROJ-123"
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: FAIL because the workflow does not yet support `evaluation_settings` or pre-Jira gate logic.

- [ ] **Step 3: Add the gate service and wire it into pre-Jira workflow execution**

```python
# src/services/requirement_gate_service.py
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RequirementGateResult:
    blocked: bool
    blocking_reason: Optional[str] = None


class RequirementGateService:
    def evaluate(self, backlog_data: Dict[str, Any]) -> RequirementGateResult:
        criteria = backlog_data.get("acceptance_criteria")
        has_criteria = isinstance(criteria, list) and any(
            str(item).strip() for item in criteria
        )
        if has_criteria:
            return RequirementGateResult(blocked=False)
        return RequirementGateResult(
            blocked=True,
            blocking_reason="Requirement quality gate blocked creation because acceptance criteria are missing.",
        )
```

```python
# src/services/requirement_workflow_service.py
self.evaluation_settings = evaluation_settings or RequirementEvaluationSettings()
self.gate_service = gate_service or RequirementGateService()

if self.evaluation_settings.gate_enabled:
    gate_result = self.gate_service.evaluate(backlog_data)
    if gate_result.blocked:
        self._set_progress_status(
            workflow_progress,
            "evaluation",
            "blocked",
            detail=gate_result.blocking_reason,
        )
        return RequirementWorkflowResult(
            success=False,
            response_text=gate_result.blocking_reason,
            backlog_data=backlog_data,
            workflow_progress=workflow_progress,
        )
```

- [ ] **Step 4: Run the targeted tests and verify they pass**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: PASS with Jira creation skipped when the gate blocks and normal execution preserved when criteria exist.

- [ ] **Step 5: Commit**

```bash
git add src/services/requirement_gate_service.py src/services/requirement_workflow_service.py tests/unit/test_requirement_workflow_service.py
git commit -m "feat: add acceptance-criteria quality gate"
```

### Task 3: Add Optional Advisory Evaluation Output

**Files:**
- Create: `src/services/requirement_quality_evaluator.py`
- Modify: `src/services/requirement_workflow_service.py`
- Test: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write failing tests for evaluation-disabled and evaluation-enabled behavior**

```python
def test_execute_backlog_data_skips_evaluation_when_disabled():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        evaluation_settings=RequirementEvaluationSettings(
            evaluation_enabled=False,
            gate_enabled=False,
        ),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert "Maturity Evaluation Results" not in result.response_text
    assert result.workflow_progress[1]["status"] == "skipped"


def test_execute_backlog_data_runs_evaluation_when_enabled():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("unused"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        evaluation_settings=RequirementEvaluationSettings(
            evaluation_enabled=True,
            gate_enabled=False,
        ),
    )

    result = service.execute_backlog_data(
        {
            "summary": "Add login auditing",
            "business_value": "Improves security traceability",
            "acceptance_criteria": ["Every login is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves security traceability",
        }
    )

    assert result.success is True
    assert "Maturity Evaluation Results" in result.response_text
    assert result.workflow_progress[1]["status"] == "completed"
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: FAIL because evaluation is always attempted when a Jira evaluation port is configured.

- [ ] **Step 3: Add an advisory evaluator and only run it when enabled**

```python
# src/services/requirement_quality_evaluator.py
class RequirementQualityEvaluator:
    def summarize(self, evaluation_result):
        return {
            "overall_score": evaluation_result.get("overall_maturity_score"),
            "strengths": evaluation_result.get("strengths", []),
            "weaknesses": evaluation_result.get("weaknesses", []),
            "recommendations": evaluation_result.get("recommendations", []),
        }
```

```python
# src/services/requirement_workflow_service.py
if self.evaluation_settings.evaluation_enabled and self.jira_evaluation_port:
    evaluation_result = self.evaluate_issue(issue_key)
    ...
else:
    self._set_progress_status(
        workflow_progress,
        "evaluation",
        "skipped",
        detail="Requirement evaluation disabled by configuration.",
    )
```

- [ ] **Step 4: Run the targeted tests and verify they pass**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: PASS with advisory output present only when evaluation is enabled.

- [ ] **Step 5: Commit**

```bash
git add src/services/requirement_quality_evaluator.py src/services/requirement_workflow_service.py tests/unit/test_requirement_workflow_service.py
git commit -m "feat: make requirement evaluation configurable"
```

### Task 4: Preserve Existing Agent Contract and Verify End-to-End Workflow Behavior

**Files:**
- Modify: `tests/unit/test_requirement_workflow_service.py`
- Test: `tests/unit/test_requirement_sdlc_agent_service.py`
- Test: `tests/unit/test_requirement_sdlc_agent_integration.py`

- [ ] **Step 1: Write a regression test that approval still delegates into workflow execution**

```python
def test_requirement_sdlc_agent_approval_surfaces_gate_failure():
    workflow_service = MagicMock()
    workflow_service.execute_backlog_data.return_value = RequirementWorkflowResult(
        success=False,
        response_text="Requirement quality gate blocked creation because acceptance criteria are missing.",
        workflow_progress=[
            {"step": "jira", "label": "Create Jira", "status": "skipped"},
            {"step": "evaluation", "label": "Evaluate Requirement", "status": "blocked"},
        ],
    )

    service = RequirementSdlcAgentService(
        llm_provider=FakeLLMProvider("{}"),
        workflow_service=workflow_service,
    )

    result = service.handle_turn(
        user_input="approve",
        conversation_history=[],
        pending_state={
            "stage": "confirmation",
            "awaiting_confirmation": True,
            "draft": {"summary": "Add login auditing", "acceptance_criteria": []},
        },
    )

    assert result.response_kind == "completed"
    assert "acceptance criteria are missing" in result.response_text.lower()
```

- [ ] **Step 2: Run the targeted regression suite and verify it fails or is incomplete**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py -q`

Expected: FAIL until workflow-level gate and evaluation toggles are fully wired and surfaced through existing responses.

- [ ] **Step 3: Adjust response text and workflow progress formatting as needed without changing the agent service responsibility split**

```python
# src/services/requirement_workflow_service.py
return RequirementWorkflowResult(
    success=False,
    response_text=(
        "Requirement quality gate blocked creation because acceptance criteria are missing. "
        "Please add at least one acceptance criterion and approve again."
    ),
    backlog_data=backlog_data,
    workflow_progress=workflow_progress,
)
```

- [ ] **Step 4: Run the final focused verification suite**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py src/services/requirement_workflow_service.py
git commit -m "test: cover requirement evaluation gate workflow"
```

## Self-Review
- Spec coverage: the plan covers env-only toggles, deterministic acceptance-criteria gating, advisory evaluation control, workflow integration, and regression coverage for the existing SDLC agent handoff.
- Placeholder scan: all tasks specify exact files, commands, and concrete code snippets; no `TODO` or deferred implementation notes remain.
- Type consistency: the plan uses `RequirementEvaluationSettings`, `RequirementGateService`, and `RequirementWorkflowResult` consistently across tasks.
