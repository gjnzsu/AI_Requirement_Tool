# Requirement SDLC Agent Confirmation Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `Approve` and `Cancel` confirmation actions to the chat UI for Requirement SDLC Agent preview turns while preserving text-based fallback behavior.

**Architecture:** Extend the request execution result with a tiny `ui_actions` contract derived from Requirement SDLC Agent runtime state, then render those actions in the existing chat message UI as inline buttons that submit ordinary chat turns. Keep execution semantics unchanged so backend confirmation still relies on `approve` and `cancel` text values.

**Tech Stack:** Python, Flask, pytest, vanilla JavaScript, existing web UI CSS

---

### Task 1: Add backend `ui_actions` contract for confirmation turns

**Files:**
- Modify: `src/webapp/runtime.py`
- Modify: `tests/unit/test_webapp_runtime.py`
- Modify: `tests/integration/api/test_chat_api.py`

- [ ] **Step 1: Write the failing runtime and API tests**

```python
def test_execute_chat_request_exposes_confirmation_ui_actions():
    result = runtime.execute_chat_request(...)
    assert result.ui_actions == [
        {"label": "Approve", "value": "approve", "kind": "primary"},
        {"label": "Cancel", "value": "cancel", "kind": "secondary"},
    ]


def test_chat_explicit_requirement_sdlc_agent_mode_returns_ui_actions(...):
    assert data["ui_actions"] == [
        {"label": "Approve", "value": "approve", "kind": "primary"},
        {"label": "Cancel", "value": "cancel", "kind": "secondary"},
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_webapp_runtime.py tests/integration/api/test_chat_api.py -q`
Expected: FAIL because `ChatExecutionResult` and `/api/chat` do not expose `ui_actions`

- [ ] **Step 3: Implement minimal runtime and API support**

```python
@dataclass
class ChatExecutionResult:
    response: str
    conversation_id: str
    chatbot: Any
    usage_info: Optional[Dict[str, Any]] = None
    ui_actions: Optional[list[dict[str, str]]] = None


def _build_ui_actions(runtime_state: Dict[str, Any]) -> Optional[list[dict[str, str]]]:
    state = (runtime_state or {}).get("requirement_sdlc_agent_state") or {}
    if state.get("stage") == "confirmation" and state.get("awaiting_confirmation"):
        return [
            {"label": "Approve", "value": "approve", "kind": "primary"},
            {"label": "Cancel", "value": "cancel", "kind": "secondary"},
        ]
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_webapp_runtime.py tests/integration/api/test_chat_api.py -q`
Expected: PASS

### Task 2: Render confirmation action buttons in the chat UI

**Files:**
- Modify: `web/static/js/app.js`
- Modify: `web/static/css/style.css`

- [ ] **Step 1: Write the failing UI-facing regression test at the contract seam**

```python
def test_chat_explicit_requirement_sdlc_agent_mode_returns_ui_actions(...):
    assert data["ui_actions"][0]["value"] == "approve"
    assert data["ui_actions"][1]["value"] == "cancel"
```

- [ ] **Step 2: Run the API test to verify it fails before frontend changes**

Run: `pytest tests/integration/api/test_chat_api.py::TestChatAPI::test_chat_explicit_requirement_sdlc_agent_mode -q`
Expected: FAIL because `ui_actions` is missing from the response

- [ ] **Step 3: Implement button rendering and click handling**

```javascript
function addMessageToUI(role, content, isLoading = false, options = {}) {
  if (role === 'assistant' && Array.isArray(options.uiActions) && options.uiActions.length) {
    const quickActionsDiv = document.createElement('div');
    quickActionsDiv.className = 'message-quick-actions';
    options.uiActions.forEach((action) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `quick-action-btn ${action.kind || 'secondary'}`;
      button.textContent = action.label;
      button.addEventListener('click', () => submitQuickAction(button, action.value));
      quickActionsDiv.appendChild(button);
    });
    contentDiv.appendChild(quickActionsDiv);
  }
}
```

- [ ] **Step 4: Update message sending so quick actions reuse normal chat requests**

```javascript
async function sendMessage(messageOverride = null) {
  const message = (messageOverride ?? chatInput.value).trim();
  ...
  addMessageToUI('assistant', data.response, false, { uiActions: data.ui_actions || [] });
}
```

- [ ] **Step 5: Run the focused backend regression suite**

Run: `pytest tests/unit/test_agent_intent_service.py tests/unit/test_webapp_runtime.py tests/unit/test_chatbot_requirement_workflow.py tests/integration/api/test_chat_api.py -q`
Expected: PASS

### Task 3: Verify SDLC-agent behavior still holds end to end at the service layer

**Files:**
- Test: `tests/unit/test_requirement_sdlc_agent_service.py`
- Test: `tests/unit/test_requirement_sdlc_agent_integration.py`

- [ ] **Step 1: Run the existing SDLC-agent service slice**

Run: `pytest tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py tests/unit/test_agent_graph_builder.py -q`
Expected: PASS and no behavior regressions in approval/cancel flow

- [ ] **Step 2: Run the combined verification slice**

Run: `pytest tests/unit/test_webapp_runtime.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_sdlc_agent_integration.py tests/unit/test_agent_graph_builder.py tests/unit/test_chatbot_requirement_workflow.py tests/integration/api/test_chat_api.py -q`
Expected: PASS
