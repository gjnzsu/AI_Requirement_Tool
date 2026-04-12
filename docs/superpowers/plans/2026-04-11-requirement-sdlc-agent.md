# Requirement SDLC Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PoC Requirement SDLC Agent as a single specialist agent with internal stages, BA-guided analysis, in-chat confirmation, and shared workflow execution.

**Architecture:** Add a staged `RequirementSdlcAgentService` that behaves as the Requirement SDLC Agent orchestration layer. It owns draft analysis, preview, confirmation, and execution handoff. Keep deterministic lifecycle execution in `RequirementWorkflowService`, model Jira/evaluation/Confluence/RAG as reusable workflow capabilities behind the agent, keep conversation-scoped pending agent state in conversation metadata/runtime state, and let `ChatbotAgent` route into the new agent without reintroducing prompt-only workflow logic.

**Tech Stack:** Python, LangGraph, LangChain message models, existing Flask runtime, SQLite-backed `MemoryManager`, pytest

---

## File Structure

### New Files
- `src/services/requirement_sdlc_agent_service.py`
  Owns BA-guided intake, staged draft progression, preview generation, confirmation parsing, and workflow handoff for the Requirement SDLC Agent.
- `tests/unit/test_requirement_sdlc_agent_service.py`
  Covers analysis, preview, approval, revision, cancellation, and execution handoff.
- `tests/unit/test_requirement_sdlc_agent_agent_integration.py`
  Covers intent routing into the new agent node and confirmation-aware follow-up turns.

### Modified Files
- `src/services/requirement_workflow_service.py`
  Add a structured entry point so the skill can execute approved draft data without regenerating it from raw chat text.
- `tests/unit/test_requirement_workflow_service.py`
  Add structured execution tests.
- `src/services/memory_manager.py`
  Add metadata update support for conversation-scoped pending skill state.
- `src/chatbot.py`
  Load and persist conversation-scoped runtime state, including the pending Requirement Lifecycle skill draft.
- `src/webapp/runtime.py`
  Snapshot and restore chatbot runtime state and sync in-memory conversation metadata.
- `tests/unit/test_webapp_runtime.py`
  Add request isolation and metadata sync coverage for skill state.
- `src/agent/intent_routing.py`
  Add explicit Requirement Lifecycle skill keywords and confirmation-aware routing hooks.
- `src/services/intent_detector.py`
  Teach LLM intent detection about `requirement_sdlc_agent`.
- `src/services/agent_intent_service.py`
  Route the new intent and short-circuit back to the Requirement SDLC Agent while staged agent state is active.
- `src/agent/graph_builder.py`
  Register the `requirement_sdlc_agent` node used by the Requirement SDLC Agent.
- `src/agent/agent_graph.py`
  Compose the new skill service, expose runtime-state import/export helpers, add the skill node, and delegate execution to the service.
- `src/services/__init__.py`
  Export the new skill service.
- `tests/unit/test_agent_intent_service.py`
  Add intent routing coverage for the new intent and pending-draft override.
- `tests/unit/test_agent_graph_builder.py`
  Add graph wiring coverage for the new skill node.
- `tests/unit/test_chatbot_requirement_workflow.py`
  Extend chatbot integration coverage to include runtime-state persistence around the new skill.

---

### Task 1: Add Structured Workflow Execution Entry Point

**Files:**
- Modify: `src/services/requirement_workflow_service.py`
- Test: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write the failing structured execution tests**

```python
def test_execute_backlog_data_runs_lifecycle_without_regenerating_backlog():
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider("{}"),
        jira_issue_port=FakeJiraIssuePort(),
        jira_evaluation_port=FakeJiraEvaluationPort(),
        confluence_page_port=FakeConfluencePagePort(),
    )

    backlog_data = {
        "summary": "Add login auditing",
        "business_value": "Improves security traceability",
        "acceptance_criteria": ["Every login is recorded"],
        "priority": "High",
        "invest_analysis": "Small and testable",
        "description": "Business Value: Improves security traceability",
    }

    result = service.execute_backlog_data(backlog_data)

    assert result.success is True
    assert result.jira_result["key"] == "PROJ-123"
    assert "Successfully created Jira issue" in result.response_text


def test_execute_delegates_generated_backlog_to_execute_backlog_data(mocker):
    service = RequirementWorkflowService(
        llm_provider=FakeLLMProvider(
            '{"summary": "Generated issue", "description": "desc", "priority": "Medium"}'
        ),
        jira_issue_port=FakeJiraIssuePort(),
    )
    execute_backlog_data = mocker.patch.object(
        service,
        "execute_backlog_data",
        return_value=RequirementWorkflowResult(success=True, response_text="ok"),
    )

    result = service.execute("create jira", [])

    assert result.response_text == "ok"
    execute_backlog_data.assert_called_once()
```

- [ ] **Step 2: Run the workflow service tests to verify they fail**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: FAIL with `AttributeError: 'RequirementWorkflowService' object has no attribute 'execute_backlog_data'`

- [ ] **Step 3: Implement `execute_backlog_data()` and refactor `execute()` to reuse it**

```python
def execute_backlog_data(self, backlog_data: Dict[str, Any]) -> RequirementWorkflowResult:
    if not self.jira_issue_port:
        return RequirementWorkflowResult(
            success=False,
            response_text=(
                "I apologize, but the Jira tool is not configured correctly. "
                "Please check your Jira credentials."
            ),
        )

    jira_result_payload = self.create_jira_issue(backlog_data)
    if not jira_result_payload.get("success"):
        return RequirementWorkflowResult(
            success=False,
            response_text=f"Failed to create Jira issue: {jira_result_payload.get('error')}",
            backlog_data=backlog_data,
            jira_result=self._legacy_result_payload(jira_result_payload),
        )

    issue_key = jira_result_payload.get("key")
    response_parts = [self._format_jira_success(jira_result_payload, backlog_data)]
    evaluation_result = None
    confluence_result = None

    if self.jira_evaluation_port:
        evaluation_result = self.evaluate_issue(issue_key)
        if "error" not in evaluation_result:
            response_parts.append(self.format_evaluation_result(evaluation_result))
            if self.confluence_page_port:
                confluence_result = self.create_confluence_page(
                    issue_key=issue_key,
                    backlog_data=backlog_data,
                    evaluation_result=evaluation_result,
                    jira_link=jira_result_payload.get("link"),
                )
                response_parts.append(self._format_confluence_result(confluence_result))

    return RequirementWorkflowResult(
        success=True,
        response_text="".join(response_parts),
        backlog_data=backlog_data,
        jira_result=self._legacy_result_payload(jira_result_payload),
        evaluation_result=evaluation_result,
        confluence_result=self._legacy_result_payload(confluence_result),
    )


def execute(self, user_input: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> RequirementWorkflowResult:
    backlog_data = self._generate_backlog_data(
        user_input=user_input,
        conversation_history=conversation_history or [],
    )
    return self.execute_backlog_data(backlog_data)
```

- [ ] **Step 4: Run the workflow service tests to verify they pass**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`

Expected: PASS

- [ ] **Step 5: Commit the structured workflow foundation**

```bash
git add src/services/requirement_workflow_service.py tests/unit/test_requirement_workflow_service.py
git commit -m "feat: add structured requirement workflow execution"
```

---

### Task 2: Persist Conversation-Scoped Skill State

**Files:**
- Modify: `src/services/memory_manager.py`
- Modify: `src/chatbot.py`
- Modify: `src/webapp/runtime.py`
- Test: `tests/unit/test_webapp_runtime.py`

- [ ] **Step 1: Write failing runtime-state persistence tests**

```python
def test_execute_chat_request_restores_runtime_state_after_request():
    runtime = AppRuntime(config=FakeConfig)
    chatbot = Mock()
    chatbot.provider_name = "openai"
    chatbot.export_runtime_state = Mock(side_effect=[{"requirement_sdlc_agent_state": {"stage": "preview"}}, {"requirement_sdlc_agent_state": {"stage": "preview"}}])
    chatbot.load_runtime_state = Mock()
    chatbot.switch_provider = Mock()
    chatbot.set_conversation_id = Mock()
    chatbot.load_conversation = Mock()
    chatbot.get_response = Mock(return_value="preview")
    runtime.memory_manager = Mock()

    runtime.execute_chat_request(
        message="turn this into a requirement",
        conversation_id="conv-123",
        model="openai",
        chatbot=chatbot,
        memory_manager=runtime.memory_manager,
    )

    chatbot.load_runtime_state.assert_called()


def test_sync_in_memory_conversation_persists_runtime_state_metadata():
    runtime = AppRuntime(config=FakeConfig)
    runtime.memory_manager = None
    runtime.conversations["conv-123"] = {"messages": [], "metadata": {}, "title": "Chat", "created_at": "2026-04-11T00:00:00"}
    chatbot = Mock()
    chatbot.conversation_history = [{"role": "assistant", "content": "preview"}]
    chatbot.export_runtime_state = Mock(return_value={"requirement_sdlc_agent_state": {"stage": "preview"}})

    runtime._sync_in_memory_conversation("conv-123", chatbot)

    assert runtime.conversations["conv-123"]["metadata"]["requirement_sdlc_agent_state"]["stage"] == "preview"
```

- [ ] **Step 2: Run the runtime tests to verify they fail**

Run: `pytest tests/unit/test_webapp_runtime.py -q`

Expected: FAIL with missing `export_runtime_state` / `load_runtime_state` handling or missing `metadata` sync

- [ ] **Step 3: Add metadata update and runtime-state load/save hooks**

```python
# src/services/memory_manager.py
def update_conversation_metadata(self, conversation_id: str, metadata: Dict) -> bool:
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE conversations
            SET metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(metadata or {}), datetime.now().isoformat(), conversation_id),
        )
    return True


# src/chatbot.py
def export_runtime_state(self) -> Dict[str, Any]:
    skill_state = None
    if self.agent and hasattr(self.agent, "export_requirement_sdlc_agent_state"):
        skill_state = self.agent.export_requirement_sdlc_agent_state()
    return {"requirement_sdlc_agent_state": skill_state}


def load_runtime_state(self, runtime_state: Optional[Dict[str, Any]]) -> None:
    if self.agent and hasattr(self.agent, "load_requirement_sdlc_agent_state"):
        self.agent.load_requirement_sdlc_agent_state((runtime_state or {}).get("requirement_sdlc_agent_state"))


def load_conversation(self, conversation_id: str) -> bool:
    conversation = self.memory_manager.get_conversation(conversation_id)
    ...
    self.load_runtime_state(conversation.get("metadata", {}))
    return True


# src/webapp/runtime.py
def _snapshot_chatbot_state(self, chatbot: Any) -> Dict[str, Any]:
    return {
        "conversation_id": getattr(chatbot, "conversation_id", None),
        "conversation_history": copy.deepcopy(getattr(chatbot, "conversation_history", [])),
        "last_usage": copy.deepcopy(getattr(chatbot, "last_usage", None)),
        "runtime_state": copy.deepcopy(getattr(chatbot, "export_runtime_state", lambda: {})()),
    }


def _restore_chatbot_state(self, chatbot: Any, snapshot: Dict[str, Any]) -> None:
    ...
    if hasattr(chatbot, "load_runtime_state"):
        chatbot.load_runtime_state(snapshot.get("runtime_state", {}))


def _load_in_memory_conversation(self, chatbot: Any, conversation_id: str) -> None:
    conversation = self.conversations.get(conversation_id, {})
    chatbot.conversation_history = copy.deepcopy(conversation.get("messages", []))
    if hasattr(chatbot, "load_runtime_state"):
        chatbot.load_runtime_state(copy.deepcopy(conversation.get("metadata", {})))


def _sync_in_memory_conversation(self, conversation_id: str, chatbot: Any) -> None:
    conversation = self.conversations.setdefault(conversation_id, {})
    conversation["messages"] = copy.deepcopy(getattr(chatbot, "conversation_history", []))
    conversation["metadata"] = copy.deepcopy(getattr(chatbot, "export_runtime_state", lambda: {})())
```

- [ ] **Step 4: Run the runtime tests to verify they pass**

Run: `pytest tests/unit/test_webapp_runtime.py -q`

Expected: PASS

- [ ] **Step 5: Commit conversation-scoped skill-state persistence**

```bash
git add src/services/memory_manager.py src/chatbot.py src/webapp/runtime.py tests/unit/test_webapp_runtime.py
git commit -m "feat: persist requirement skill state per conversation"
```

---

### Task 3: Build the Requirement SDLC Agent Service

**Files:**
- Create: `src/services/requirement_sdlc_agent_service.py`
- Modify: `src/services/__init__.py`
- Modify: `src/services/requirement_workflow_service.py`
- Test: `tests/unit/test_requirement_sdlc_agent_service.py`

- [ ] **Step 1: Write failing skill-service tests**

```python
def test_handle_turn_creates_preview_and_waits_for_confirmation():
    llm = FakeSkillLLM(
        """
        {
          "status": "ready_for_confirmation",
          "assistant_message": "Preview ready",
          "draft": {
            "summary": "Add login auditing",
            "problem_goal": "Track all login attempts",
            "business_value": "Improves traceability",
            "scope_notes": "Authentication only",
            "acceptance_criteria": ["Every login attempt is recorded"],
            "assumptions": ["Existing auth system remains unchanged"],
            "open_questions": [],
            "priority": "High"
          }
        }
        """
    )
    workflow_service = Mock()
    service = RequirementSdlcAgentService(llm_provider=llm, workflow_service=workflow_service)

    result = service.handle_turn(
        user_input="Help me turn this into a requirement for login auditing",
        conversation_history=[],
        pending_state=None,
    )

    assert result.response_kind == "preview"
    assert result.pending_state["awaiting_confirmation"] is True
    workflow_service.execute_backlog_data.assert_not_called()


def test_handle_turn_approval_executes_structured_workflow():
    workflow_service = Mock()
    workflow_service.execute_backlog_data.return_value = RequirementWorkflowResult(
        success=True,
        response_text="workflow complete",
        backlog_data={"summary": "Add login auditing"},
        jira_result={"success": True, "key": "PROJ-123", "link": "https://jira.example/browse/PROJ-123"},
        confluence_result={"success": True, "title": "PROJ-123: Add login auditing", "link": "https://wiki.example/pages/123"},
    )
    service = RequirementSdlcAgentService(llm_provider=FakeSkillLLM("{}"), workflow_service=workflow_service)
    pending_state = {
        "stage": "confirmation",
        "awaiting_confirmation": True,
        "draft": {
            "summary": "Add login auditing",
            "business_value": "Improves traceability",
            "acceptance_criteria": ["Every login attempt is recorded"],
            "priority": "High",
            "invest_analysis": "Small and testable",
            "description": "Business Value: Improves traceability",
        },
    }

    result = service.handle_turn(
        user_input="approve",
        conversation_history=[],
        pending_state=pending_state,
    )

    assert result.response_kind == "completed"
    assert result.pending_state is None
    workflow_service.execute_backlog_data.assert_called_once()
```

- [ ] **Step 2: Run the new skill-service tests to verify they fail**

Run: `pytest tests/unit/test_requirement_sdlc_agent_service.py -q`

Expected: FAIL because `RequirementSdlcAgentService` does not exist yet

- [ ] **Step 3: Create the staged skill service**

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RequirementSdlcAgentTurnResult:
    response_text: str
    response_kind: str
    pending_state: Optional[Dict[str, Any]]
    workflow_result: Optional[Any] = None


class RequirementSdlcAgentService:
    def __init__(self, *, llm_provider: Any, workflow_service: Any) -> None:
        self.llm_provider = llm_provider
        self.workflow_service = workflow_service

    def handle_turn(
        self,
        *,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        pending_state: Optional[Dict[str, Any]],
    ) -> RequirementSdlcAgentTurnResult:
        if pending_state and pending_state.get("awaiting_confirmation"):
            return self._handle_confirmation_turn(user_input, pending_state)

        analysis = self._analyze_requirement(user_input, conversation_history)
        draft = self._normalize_draft(analysis["draft"])

        if analysis["status"] == "needs_information":
            return RequirementSdlcAgentTurnResult(
                response_text=analysis["assistant_message"],
                response_kind="question",
                pending_state={"stage": "analysis", "awaiting_confirmation": False, "draft": draft},
            )

        preview = self._build_preview(draft)
        return RequirementSdlcAgentTurnResult(
            response_text=preview,
            response_kind="preview",
            pending_state={"stage": "confirmation", "awaiting_confirmation": True, "draft": draft},
        )

    def _handle_confirmation_turn(self, user_input: str, pending_state: Dict[str, Any]) -> RequirementSdlcAgentTurnResult:
        normalized = user_input.strip().lower()
        if normalized in {"cancel", "stop", "do not create anything"}:
            return RequirementSdlcAgentTurnResult(
                response_text="Cancelled the requirement lifecycle draft. Nothing was created.",
                response_kind="cancelled",
                pending_state=None,
            )
        if normalized in {"approve", "yes", "go ahead", "proceed"}:
            workflow_result = self.workflow_service.execute_backlog_data(pending_state["draft"])
            return RequirementSdlcAgentTurnResult(
                response_text=workflow_result.response_text,
                response_kind="completed",
                pending_state=None,
                workflow_result=workflow_result,
            )
        revised_state = dict(pending_state)
        revised_state["awaiting_confirmation"] = False
        revised_state["stage"] = "analysis"
        return RequirementSdlcAgentTurnResult(
            response_text=f"I've captured your revision request: {user_input}",
            response_kind="revision",
            pending_state=revised_state,
        )
```

- [ ] **Step 4: Run the new skill-service tests to verify they pass**

Run: `pytest tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_workflow_service.py -q`

Expected: PASS

- [ ] **Step 5: Commit the skill-service foundation**

```bash
git add src/services/requirement_sdlc_agent_service.py src/services/__init__.py src/services/requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_workflow_service.py
git commit -m "feat: add staged requirement lifecycle skill service"
```

---

### Task 4: Route the Agent Into the Requirement SDLC Agent

**Files:**
- Modify: `src/agent/intent_routing.py`
- Modify: `src/services/intent_detector.py`
- Modify: `src/services/agent_intent_service.py`
- Modify: `src/agent/graph_builder.py`
- Modify: `src/agent/agent_graph.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/test_agent_intent_service.py`
- Test: `tests/unit/test_agent_graph_builder.py`
- Test: `tests/unit/test_requirement_sdlc_agent_agent_integration.py`

- [ ] **Step 1: Write failing routing and agent integration tests**

```python
def test_route_after_intent_returns_requirement_sdlc_agent():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=False),
    )

    route = service.route_after_intent({"intent": "requirement_sdlc_agent"})

    assert route == "requirement_sdlc_agent"


def test_detect_intent_short_circuits_to_skill_when_confirmation_pending():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value=None),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=True),
    )

    state = service.detect_intent({"user_input": "approve", "messages": []})

    assert state["intent"] == "requirement_sdlc_agent"
```

- [ ] **Step 2: Run the intent and graph tests to verify they fail**

Run: `pytest tests/unit/test_agent_intent_service.py tests/unit/test_agent_graph_builder.py tests/unit/test_requirement_sdlc_agent_agent_integration.py -q`

Expected: FAIL because the new intent, route, and graph node do not exist yet

- [ ] **Step 3: Add the intent, graph node, and agent delegation**

```python
# src/agent/intent_routing.py
REQUIREMENT_SKILL_KEYWORDS = [
    "requirement lifecycle",
    "turn this into a requirement",
    "help me turn this into a requirement",
    "draft a ticket and docs",
    "draft requirement",
    "requirement analysis",
]

def detect_keyword_intent(...):
    ...
    if any(keyword in normalized_input for keyword in REQUIREMENT_SKILL_KEYWORDS):
        return "requirement_sdlc_agent"


# src/services/intent_detector.py
SUPPORTED_INTENTS = {
    "jira_creation",
    "rag_query",
    "general_chat",
    "coze_agent",
    "requirement_sdlc_agent",
}


# src/services/agent_intent_service.py
def __init__(..., has_pending_requirement_sdlc_agent_state: Callable[[], bool]) -> None:
    ...
    self.has_pending_requirement_sdlc_agent_state = has_pending_requirement_sdlc_agent_state

def detect_intent(self, state: Dict[str, Any]) -> Dict[str, Any]:
    if self.has_pending_requirement_sdlc_agent_state():
        state["intent"] = "requirement_sdlc_agent"
        return state
    ...

def route_after_intent(self, state: Dict[str, Any]) -> str:
    intent = state.get("intent", "general_chat")
    if intent == "requirement_sdlc_agent":
        return "requirement_sdlc_agent"
    ...


# src/agent/graph_builder.py
graph.add_node("requirement_sdlc_agent", handle_requirement_sdlc_agent)
graph.add_conditional_edges(
    "intent_detection",
    route_after_intent,
    {
        "general_chat": "general_chat",
        "jira_creation": "jira_creation",
        "rag_query": "rag_query",
        "coze_agent": "coze_agent",
        "requirement_sdlc_agent": "requirement_sdlc_agent",
    },
)
graph.add_edge("requirement_sdlc_agent", END)


# src/agent/agent_graph.py
self.requirement_sdlc_agent_service = RequirementSdlcAgentService(
    llm_provider=self.llm,
    workflow_service=self.requirement_workflow_service,
)

def load_requirement_sdlc_agent_state(self, state: Optional[Dict[str, Any]]) -> None:
    self._requirement_sdlc_agent_state = state

def export_requirement_sdlc_agent_state(self) -> Optional[Dict[str, Any]]:
    return copy.deepcopy(getattr(self, "_requirement_sdlc_agent_state", None))

def _handle_requirement_sdlc_agent(self, state: AgentState) -> AgentState:
    result = self.requirement_sdlc_agent_service.handle_turn(
        user_input=state.get("user_input", ""),
        conversation_history=state.get("conversation_history", []),
        pending_state=self.export_requirement_sdlc_agent_state(),
    )
    self.load_requirement_sdlc_agent_state(result.pending_state)
    state["messages"].append(AIMessage(content=result.response_text))
    return state
```

- [ ] **Step 4: Run the routing and integration tests to verify they pass**

Run: `pytest tests/unit/test_agent_intent_service.py tests/unit/test_agent_graph_builder.py tests/unit/test_requirement_sdlc_agent_agent_integration.py -q`

Expected: PASS

- [ ] **Step 5: Commit the Requirement Lifecycle skill integration**

```bash
git add src/agent/intent_routing.py src/services/intent_detector.py src/services/agent_intent_service.py src/agent/graph_builder.py src/agent/agent_graph.py src/services/__init__.py tests/unit/test_agent_intent_service.py tests/unit/test_agent_graph_builder.py tests/unit/test_requirement_sdlc_agent_agent_integration.py
git commit -m "feat: route chatbot agent into requirement lifecycle skill"
```

---

### Task 5: Verify Chatbot-Level Behavior End-to-End

**Files:**
- Modify: `tests/unit/test_chatbot_requirement_workflow.py`
- Modify: `tests/unit/test_webapp_runtime.py`
- Test: `tests/unit/test_requirement_sdlc_agent_service.py`
- Test: `tests/unit/test_requirement_workflow_service.py`
- Test: `tests/unit/test_agent_intent_service.py`
- Test: `tests/unit/test_agent_graph_builder.py`
- Test: `tests/unit/test_requirement_sdlc_agent_agent_integration.py`

- [ ] **Step 1: Add final chatbot-level regression tests**

```python
def test_chatbot_persists_requirement_sdlc_agent_state_across_conversation_loads():
    memory_manager = Mock()
    memory_manager.get_conversation.return_value = {
        "id": "conv-123",
        "title": "Skill chat",
        "summary": None,
        "metadata": {"requirement_sdlc_agent_state": {"stage": "confirmation", "awaiting_confirmation": True}},
        "messages": [{"role": "user", "content": "turn this into a requirement"}],
    }

    chatbot = Chatbot.__new__(Chatbot)
    chatbot.memory_manager = memory_manager
    chatbot.use_persistent_memory = True
    chatbot.conversation_history = []
    chatbot.conversation_id = None
    chatbot.agent = Mock()

    chatbot.load_conversation("conv-123")

    chatbot.agent.load_requirement_sdlc_agent_state.assert_called_once_with(
        {"stage": "confirmation", "awaiting_confirmation": True}
    )
```

- [ ] **Step 2: Run the focused Requirement Lifecycle skill suite**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_agent_intent_service.py tests/unit/test_agent_graph_builder.py tests/unit/test_requirement_sdlc_agent_agent_integration.py tests/unit/test_webapp_runtime.py tests/unit/test_chatbot_requirement_workflow.py -q`

Expected: PASS

- [ ] **Step 3: Run the broader agent/chatbot regression suite**

Run: `pytest tests/unit/test_chat_flow_services.py tests/unit/test_agent_chat_flow_delegation.py tests/unit/test_agent_confluence_nodes.py tests/unit/test_agent_jira_nodes.py tests/unit/test_agent_requirement_workflow.py tests/unit/test_runtime_composition.py tests/integration/agent/test_agent_basic.py -q -n auto`

Expected: PASS

- [ ] **Step 4: Record the verification outcome in the branch notes**

```text
Focused skill suite should prove:
- preview and confirmation state persist per conversation
- approval triggers structured workflow execution once
- routing returns to the skill while confirmation is pending
- existing general chat / Jira / Confluence flows still pass regression coverage
```

- [ ] **Step 5: Commit the final verification updates**

```bash
git add tests/unit/test_chatbot_requirement_workflow.py tests/unit/test_webapp_runtime.py tests/unit/test_requirement_sdlc_agent_service.py tests/unit/test_requirement_workflow_service.py tests/unit/test_agent_intent_service.py tests/unit/test_agent_graph_builder.py tests/unit/test_requirement_sdlc_agent_agent_integration.py
git commit -m "test: verify requirement lifecycle skill conversation flow"
```

---

## Self-Review

### Spec Coverage
- Explicit and automatic routing: Task 4
- BA-guided staged skill flow: Task 3
- One in-chat confirmation gate: Task 3 and Task 4
- Shared workflow service as execution engine: Task 1 and Task 3
- Conversation-scoped pending draft state: Task 2
- Regression safety for chatbot/runtime/agent flows: Task 5

### Placeholder Scan
- No `TBD`, `TODO`, or deferred implementation notes remain in the task steps.
- Each code-changing step includes concrete code snippets or signatures.
- Each verification step includes an exact command and expected outcome.

### Type Consistency
- Intent string is consistently `requirement_sdlc_agent`
- Persistent state key is consistently `requirement_sdlc_agent_state`
- Structured workflow entry point is consistently `execute_backlog_data`
- Skill turn method is consistently `handle_turn`

