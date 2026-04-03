# Requirement Workflow Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize the AI requirement Jira/Confluence workflow in one service and then shrink `ChatbotAgent` by moving node responsibilities into smaller modules without changing runtime behavior.

**Architecture:** Phase 1 introduces `RequirementWorkflowService` as an application service used by `Chatbot` and `ChatbotAgent`. Phase 2 extracts agent node helpers/modules so `agent_graph.py` becomes graph wiring plus orchestration state, while business logic lives in focused collaborators.

**Tech Stack:** Python, pytest, LangGraph, LangChain, Flask, Jira/Confluence tools, MCP integration.

---

### Task 1: Add Shared Requirement Workflow Service

**Files:**
- Create: `src/services/requirement_workflow_service.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write failing tests for successful workflow and failure cases**

```python
from src.services.requirement_workflow_service import RequirementWorkflowService

def test_execute_creates_jira_evaluates_and_creates_confluence():
    service = RequirementWorkflowService(...)
    result = service.execute("create jira", [{"role": "user", "content": "need auth feature"}])
    assert result.success is True
    assert result.jira_result["key"] == "PROJ-123"
    assert "Successfully created Jira issue" in result.response_text

def test_execute_returns_failure_when_backlog_json_is_invalid():
    service = RequirementWorkflowService(...)
    result = service.execute("create jira", [])
    assert result.success is False
    assert "Error processing Jira creation request" in result.response_text
```

- [ ] **Step 2: Run service tests and verify they fail because the module does not exist yet**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: FAIL with `ModuleNotFoundError` or import error for `src.services.requirement_workflow_service`.

- [ ] **Step 3: Implement the service with dependency injection and response formatting**

```python
class RequirementWorkflowService:
    def execute(self, user_input, conversation_history):
        backlog_data = self.generate_backlog_data(user_input, conversation_history)
        jira_result = self.create_jira_issue(backlog_data)
        evaluation = self.evaluate_issue(jira_result)
        confluence_result = self.create_confluence_page(jira_result, backlog_data, evaluation)
        return RequirementWorkflowResult(...)
```

- [ ] **Step 4: Run service tests and verify they pass**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: PASS.

### Task 2: Refactor `Chatbot` to Delegate Jira Workflow

**Files:**
- Modify: `src/chatbot.py`
- Test: `tests/unit/test_chatbot_requirement_workflow.py`

- [ ] **Step 1: Write a failing delegation test for `Chatbot._handle_jira_creation()`**

```python
def test_handle_jira_creation_delegates_to_requirement_workflow_service():
    chatbot = Chatbot(...)
    chatbot.requirement_workflow_service = Mock()
    chatbot.requirement_workflow_service.execute.return_value.response_text = "ok"
    assert chatbot._handle_jira_creation("create jira") == "ok"
```

- [ ] **Step 2: Run the chatbot delegation test and verify it fails**

Run: `pytest tests/unit/test_chatbot_requirement_workflow.py -q`

Expected: FAIL because `Chatbot` does not yet delegate to the new service.

- [ ] **Step 3: Wire `RequirementWorkflowService` into `Chatbot` tool initialization and replace the duplicated Jira workflow implementation with a thin adapter**

```python
self.requirement_workflow_service = RequirementWorkflowService(...)

def _handle_jira_creation(self, user_input):
    return self.requirement_workflow_service.execute(user_input, self.conversation_history).response_text
```

- [ ] **Step 4: Run targeted chatbot/service tests**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_chatbot_requirement_workflow.py -q`

Expected: PASS.

### Task 3: Introduce Agent Requirement Workflow Helpers

**Files:**
- Create: `src/agent/requirement_workflow.py`
- Modify: `src/agent/__init__.py`
- Modify: `src/agent/agent_graph.py`
- Test: `tests/unit/test_agent_requirement_workflow.py`

- [ ] **Step 1: Write failing tests for backlog prompt/context helpers and Confluence content rendering**

```python
from src.agent.requirement_workflow import build_requirement_context

def test_build_requirement_context_includes_recent_messages_and_history():
    context = build_requirement_context(messages=[...], conversation_history=[...])
    assert "Conversation History" in context
```

- [ ] **Step 2: Run the new agent helper tests and verify they fail**

Run: `pytest tests/unit/test_agent_requirement_workflow.py -q`

Expected: FAIL because the helper module does not exist yet.

- [ ] **Step 3: Extract context/prompt/confluence formatting helpers from `ChatbotAgent` into the new module and delegate to them**

```python
from src.agent.requirement_workflow import (
    build_requirement_context,
    build_backlog_generation_prompt,
)
```

- [ ] **Step 4: Run helper tests and existing intent tests**

Run: `pytest tests/unit/test_agent_requirement_workflow.py tests/unit/test_agent_intent_keywords.py -q`

Expected: PASS.

### Task 4: Verification and Cleanup

**Files:**
- Modify only files already touched by Tasks 1-3 if cleanup is needed.

- [ ] **Step 1: Run targeted unit tests**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_chatbot_requirement_workflow.py tests/unit/test_agent_requirement_workflow.py tests/unit/test_agent_intent_keywords.py -q`

Expected: PASS.

- [ ] **Step 2: Run one smoke integration test around agent/chatbot behavior**

Run: `pytest tests/integration/agent/test_agent_basic.py -q`

Expected: PASS or a known environment-skip. Investigate any unexpected failure before completion.

- [ ] **Step 3: Review git diff for unrelated edits and keep only refactor changes**

Run: `git status --short`

Expected: only the planned files are modified or added.
