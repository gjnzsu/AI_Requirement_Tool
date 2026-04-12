# Requirement SDLC Agent Step Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a post-run step-progress summary for the Requirement SDLC Agent so users can see the outcome of `Jira -> Evaluate -> Confluence -> RAG` after approving a draft.

**Architecture:** Extend the Requirement workflow result with a structured `workflow_progress` payload that records each step's status, detail, and relevant links. Thread that payload through the SDLC-agent execution path, request runtime, and `/api/chat` response, then render it in the chat UI as a compact progress panel beneath the assistant message. Keep the current final response text unchanged and avoid streaming or polling.

**Tech Stack:** Python, Flask, pytest, vanilla JavaScript, existing web UI CSS

---

### Task 1: Add structured workflow progress to the workflow service

**Files:**
- Modify: `src/services/requirement_workflow_service.py`
- Modify: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write the failing workflow-service tests**

```python
def test_execute_backlog_data_returns_workflow_progress_for_successful_run():
    result = service.execute_backlog_data(backlog_data)

    assert result.workflow_progress == [
        {"step": "jira", "label": "Create Jira", "status": "completed", "link": "https://jira.example/browse/PROJ-123"},
        {"step": "evaluation", "label": "Evaluate Requirement", "status": "completed"},
        {"step": "confluence", "label": "Create Confluence Page", "status": "completed", "link": "https://wiki.example/pages/123"},
        {"step": "rag", "label": "Ingest to RAG", "status": "skipped"},
    ]


def test_execute_backlog_data_marks_downstream_steps_skipped_when_jira_fails():
    result = service.execute_backlog_data(backlog_data)

    assert result.workflow_progress[0]["status"] == "failed"
    assert result.workflow_progress[1]["status"] == "skipped"
    assert result.workflow_progress[2]["status"] == "skipped"
    assert result.workflow_progress[3]["status"] == "skipped"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`
Expected: FAIL because `RequirementWorkflowResult` does not expose `workflow_progress`

- [ ] **Step 3: Implement the minimal workflow-progress model**

```python
@dataclass
class RequirementWorkflowResult:
    success: bool
    response_text: str
    backlog_data: Optional[Dict[str, Any]] = None
    jira_result: Optional[Dict[str, Any]] = None
    evaluation_result: Optional[Dict[str, Any]] = None
    confluence_result: Optional[Dict[str, Any]] = None
    workflow_progress: Optional[List[Dict[str, Any]]] = None
```

```python
progress = [
    {"step": "jira", "label": "Create Jira", "status": "pending"},
    {"step": "evaluation", "label": "Evaluate Requirement", "status": "pending"},
    {"step": "confluence", "label": "Create Confluence Page", "status": "pending"},
    {"step": "rag", "label": "Ingest to RAG", "status": "skipped"},
]
```

- [ ] **Step 4: Update progress status in each workflow branch**

```python
progress[0]["status"] = "completed"
progress[0]["link"] = jira_result_payload.get("link")

progress[1]["status"] = "completed"

progress[2]["status"] = "failed"
progress[2]["detail"] = confluence_result.get("error", "Unknown error")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`
Expected: PASS

### Task 2: Thread progress through runtime and API response

**Files:**
- Modify: `src/agent/agent_graph.py`
- Modify: `src/webapp/runtime.py`
- Modify: `app.py`
- Modify: `tests/unit/test_webapp_runtime.py`
- Modify: `tests/integration/api/test_chat_api.py`

- [ ] **Step 1: Write the failing request/runtime tests**

```python
def test_execute_chat_request_exposes_workflow_progress():
    result = runtime.execute_chat_request(...)
    assert result.workflow_progress == [
        {"step": "jira", "label": "Create Jira", "status": "completed"},
    ]


def test_chat_explicit_requirement_sdlc_agent_mode_returns_workflow_progress(...):
    assert data["workflow_progress"] == [
        {"step": "jira", "label": "Create Jira", "status": "completed"},
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_webapp_runtime.py tests/integration/api/test_chat_api.py -q`
Expected: FAIL because `workflow_progress` is not propagated through runtime/API

- [ ] **Step 3: Persist the latest workflow result on the agent path**

```python
class ChatbotAgent:
    def __init__(...):
        self._latest_requirement_workflow_result = None

    def _handle_requirement_sdlc_agent(...):
        ...
        self._latest_requirement_workflow_result = result.workflow_result

    def export_runtime_state(...):
        ...
```

- [ ] **Step 4: Surface workflow progress in the request result and API JSON**

```python
workflow_progress = copy.deepcopy(
    getattr(getattr(chatbot, "agent", None), "_latest_requirement_workflow_result", None).workflow_progress
    if getattr(getattr(chatbot, "agent", None), "_latest_requirement_workflow_result", None)
    else None
)
```

```python
return jsonify({
    "response": response,
    "conversation_id": conversation_id,
    "agent_mode": agent_mode,
    "ui_actions": execution_result.ui_actions,
    "workflow_progress": execution_result.workflow_progress,
    "timestamp": datetime.now().isoformat(),
})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_webapp_runtime.py tests/integration/api/test_chat_api.py -q`
Expected: PASS

### Task 3: Render the progress panel in the chat UI

**Files:**
- Modify: `web/static/js/app.js`
- Modify: `web/static/css/style.css`

- [ ] **Step 1: Extend assistant-message rendering to accept progress payload**

```javascript
addMessageToUI('assistant', data.response, false, {
  uiActions: data.ui_actions || [],
  workflowProgress: data.workflow_progress || []
});
```

- [ ] **Step 2: Implement compact progress rendering**

```javascript
if (role === 'assistant' && Array.isArray(options.workflowProgress) && options.workflowProgress.length > 0) {
  const progressDiv = document.createElement('div');
  progressDiv.className = 'workflow-progress';
  options.workflowProgress.forEach((step) => {
    const item = document.createElement('div');
    item.className = `workflow-progress-item ${step.status}`;
    item.innerHTML = `<span class="workflow-step-label">${step.label}</span><span class="workflow-step-status">${step.status}</span>`;
    progressDiv.appendChild(item);
  });
  contentDiv.appendChild(progressDiv);
}
```

- [ ] **Step 3: Style completed, failed, and skipped states**

```css
.workflow-progress-item.completed { border-color: #16a34a; }
.workflow-progress-item.failed { border-color: #dc2626; }
.workflow-progress-item.skipped { border-color: #9ca3af; }
```

- [ ] **Step 4: Verify no regression in confirmation buttons**

Run: `pytest tests/integration/api/test_chat_api.py -q`
Expected: PASS and existing `ui_actions` contract remains unchanged

### Task 4: Run the combined verification slice

**Files:**
- Test: `tests/unit/test_requirement_workflow_service.py`
- Test: `tests/unit/test_requirement_sdlc_agent_service.py`
- Test: `tests/unit/test_requirement_sdlc_agent_integration.py`
- Test: `tests/unit/test_webapp_runtime.py`
- Test: `tests/integration/api/test_chat_api.py`

- [ ] **Step 1: Run the workflow and SDLC-agent verification slice**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py tests/unit/test_webapp_runtime.py tests/integration/api/test_chat_api.py -q`
Expected: PASS

- [ ] **Step 2: Run the broader routing/regression slice**

Run: `pytest tests/unit/test_agent_intent_service.py tests/unit/test_agent_graph_builder.py tests/unit/test_chatbot_requirement_workflow.py tests/unit/test_requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py tests/unit/test_webapp_runtime.py tests/integration/api/test_chat_api.py -q`
Expected: PASS
