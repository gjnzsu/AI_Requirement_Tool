# Phase 3a Architecture Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce stable Jira/Confluence/evaluation/RAG ports plus fallback adapters and centralized composition so agent and workflow logic stop owning MCP-vs-direct transport policy.

**Architecture:** Add a small application boundary under `src/application/ports`, concrete fallback adapters under `src/adapters`, and a composition helper under `src/runtime/composition.py`. Keep the current public API and response text stable while migrating `RequirementWorkflowService`, `Chatbot`, and `ChatbotAgent` to depend on those composed abstractions.

**Tech Stack:** Python, Flask, LangGraph, existing Jira/Confluence tools, MCP integration, pytest

---

### Task 1: Lock Behavior With New Adapter-Facing Tests

**Files:**
- Create: `tests/unit/test_jira_issue_adapter.py`
- Create: `tests/unit/test_confluence_page_adapter.py`
- Create: `tests/unit/test_runtime_composition.py`
- Modify: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Write failing tests for the new Jira port adapter shape**

```python
from src.adapters.jira.fallback_jira_issue_adapter import FallbackJiraIssueAdapter


def test_fallback_jira_issue_adapter_uses_mcp_result_before_direct_tool():
    ...
```

- [ ] **Step 2: Run the new Jira adapter tests to verify they fail**

Run: `pytest tests/unit/test_jira_issue_adapter.py -q`
Expected: FAIL with `ModuleNotFoundError` for `src.adapters.jira.fallback_jira_issue_adapter`

- [ ] **Step 3: Write failing tests for the new Confluence port adapter shape**

```python
from src.adapters.confluence.fallback_confluence_page_adapter import FallbackConfluencePageAdapter


def test_fallback_confluence_page_adapter_uses_mcp_before_direct_api():
    ...
```

- [ ] **Step 4: Run the new Confluence adapter tests to verify they fail**

Run: `pytest tests/unit/test_confluence_page_adapter.py -q`
Expected: FAIL with `ModuleNotFoundError` for `src.adapters.confluence.fallback_confluence_page_adapter`

- [ ] **Step 5: Extend workflow service tests to use port-style dependencies**

```python
service = RequirementWorkflowService(
    llm_provider=llm_provider,
    jira_issue_port=jira_issue_port,
    jira_evaluation_port=evaluation_port,
    confluence_page_port=confluence_page_port,
)
```

- [ ] **Step 6: Run the workflow service tests to verify they fail for the new constructor contract**

Run: `pytest tests/unit/test_requirement_workflow_service.py -q`
Expected: FAIL with unexpected keyword arguments or missing port attributes

- [ ] **Step 7: Write a failing composition smoke test**

```python
from src.runtime.composition import build_application_services


def test_build_application_services_returns_workflow_service_and_ports():
    ...
```

- [ ] **Step 8: Run the composition tests to verify they fail**

Run: `pytest tests/unit/test_runtime_composition.py -q`
Expected: FAIL with `ModuleNotFoundError` for `src.runtime.composition`

### Task 2: Introduce Application Ports and Stable Result DTOs

**Files:**
- Create: `src/application/__init__.py`
- Create: `src/application/ports/__init__.py`
- Create: `src/application/ports/jira_issue_port.py`
- Create: `src/application/ports/confluence_page_port.py`
- Create: `src/application/ports/jira_evaluation_port.py`
- Create: `src/application/ports/rag_ingestion_port.py`
- Create: `src/application/ports/result_types.py`

- [ ] **Step 1: Add the shared Jira/Confluence result dataclasses and protocols**

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class JiraIssueResult:
    success: bool
    key: Optional[str] = None
    link: Optional[str] = None
    error: Optional[str] = None
    tool_used: Optional[str] = None
    raw_result: Optional[Dict[str, Any]] = None


class JiraIssuePort(Protocol):
    def create_issue(self, backlog_data: Dict[str, Any]) -> JiraIssueResult:
        ...
```

- [ ] **Step 2: Export the port types through `src/application/ports/__init__.py`**

```python
from .jira_issue_port import JiraIssuePort
from .confluence_page_port import ConfluencePagePort
from .jira_evaluation_port import JiraEvaluationPort
from .rag_ingestion_port import RagIngestionPort
from .result_types import JiraIssueResult, ConfluencePageResult
```

- [ ] **Step 3: Run the adapter and workflow tests**

Run: `pytest tests/unit/test_jira_issue_adapter.py tests/unit/test_confluence_page_adapter.py tests/unit/test_requirement_workflow_service.py -q`
Expected: FAIL because adapters and service wiring are still missing

### Task 3: Implement Jira and Confluence Fallback Adapters

**Files:**
- Create: `src/adapters/__init__.py`
- Create: `src/adapters/jira/__init__.py`
- Create: `src/adapters/jira/direct_jira_issue_adapter.py`
- Create: `src/adapters/jira/fallback_jira_issue_adapter.py`
- Create: `src/adapters/confluence/__init__.py`
- Create: `src/adapters/confluence/direct_confluence_page_adapter.py`
- Create: `src/adapters/confluence/fallback_confluence_page_adapter.py`
- Create: `src/adapters/evaluation/__init__.py`
- Create: `src/adapters/evaluation/jira_evaluation_adapter.py`

- [ ] **Step 1: Implement the direct Jira adapter using the existing `JiraTool`**

```python
class DirectJiraIssueAdapter:
    def __init__(self, jira_tool):
        self.jira_tool = jira_tool

    def create_issue(self, backlog_data):
        result = self.jira_tool.create_issue(
            summary=backlog_data.get("summary", "Untitled Issue"),
            description=backlog_data.get("description", ""),
            priority=backlog_data.get("priority", "Medium"),
        )
        return JiraIssueResult(
            success=bool(result.get("success")),
            key=result.get("key"),
            link=result.get("link"),
            error=result.get("error"),
            tool_used=result.get("tool_used", "Direct API"),
            raw_result=result,
        )
```

- [ ] **Step 2: Implement the fallback Jira adapter by wrapping the existing node helpers**

```python
class FallbackJiraIssueAdapter:
    def create_issue(self, backlog_data):
        if self.use_mcp and self.mcp_integration and initialize_jira_mcp_integration(...):
            tool = select_mcp_jira_tool(self.mcp_integration)
            if tool:
                result = invoke_mcp_jira_tool(...)
                if result:
                    return JiraIssueResult(...)
        return self.direct_adapter.create_issue(backlog_data)
```

- [ ] **Step 3: Implement the direct Confluence adapter using the existing `ConfluenceTool`**

```python
class DirectConfluencePageAdapter:
    def create_page(self, page_title, confluence_content):
        result = create_confluence_page_via_direct_api(...)
        return ConfluencePageResult(...)
```

- [ ] **Step 4: Implement the fallback Confluence adapter by wrapping the existing node helpers**

```python
class FallbackConfluencePageAdapter:
    def create_page(self, page_title, confluence_content):
        if self.use_mcp and self.mcp_integration and initialize_confluence_mcp_integration(...):
            tool = select_mcp_confluence_tool(self.mcp_integration)
            if tool:
                result = invoke_mcp_confluence_tool(...)
                if result:
                    return ConfluencePageResult(...)
        return self.direct_adapter.create_page(page_title, confluence_content)
```

- [ ] **Step 5: Implement the Jira evaluation adapter**

```python
class JiraEvaluationAdapter:
    def load_issue(self, issue_key):
        issue = self.jira_evaluator.jira.issue(issue_key)
        return {...}

    def evaluate_issue(self, issue_key):
        return self.jira_evaluator.evaluate_maturity(self.load_issue(issue_key))
```

- [ ] **Step 6: Run the new adapter tests**

Run: `pytest tests/unit/test_jira_issue_adapter.py tests/unit/test_confluence_page_adapter.py -q`
Expected: PASS

### Task 4: Migrate `RequirementWorkflowService` to Ports

**Files:**
- Modify: `src/services/requirement_workflow_service.py`
- Modify: `src/services/__init__.py`
- Modify: `tests/unit/test_requirement_workflow_service.py`

- [ ] **Step 1: Update the service constructor to accept ports first and legacy tools as compatibility fallbacks**

```python
def __init__(
    self,
    llm_provider,
    jira_issue_port=None,
    jira_evaluation_port=None,
    confluence_page_port=None,
    jira_tool=None,
    jira_evaluator=None,
    confluence_tool=None,
):
    self.jira_issue_port = jira_issue_port or _LegacyJiraIssuePort(jira_tool)
    ...
```

- [ ] **Step 2: Replace direct tool calls with port calls**

```python
jira_result = self.jira_issue_port.create_issue(backlog_data)
if not jira_result.success:
    ...
evaluation_result = self.jira_evaluation_port.evaluate_issue(issue_key)
confluence_result = self.confluence_page_port.create_page(page_title, confluence_content)
```

- [ ] **Step 3: Preserve the existing `RequirementWorkflowResult` payload shape**

```python
return RequirementWorkflowResult(
    success=True,
    response_text="".join(response_parts),
    backlog_data=backlog_data,
    jira_result=jira_result.raw_result or {...},
    evaluation_result=evaluation_result,
    confluence_result=confluence_result.raw_result if confluence_result else None,
)
```

- [ ] **Step 4: Run the workflow unit tests**

Run: `pytest tests/unit/test_requirement_workflow_service.py tests/unit/test_chatbot_requirement_workflow.py -q`
Expected: PASS

### Task 5: Add Centralized Composition Wiring

**Files:**
- Create: `src/runtime/__init__.py`
- Create: `src/runtime/composition.py`
- Modify: `src/chatbot.py`
- Modify: `src/agent/agent_graph.py`
- Modify: `src/webapp/runtime.py`
- Modify: `tests/unit/test_runtime_composition.py`

- [ ] **Step 1: Add a composition builder that assembles tools, adapters, and services**

```python
def build_application_services(*, config, llm_provider, jira_tool=None, confluence_tool=None, jira_evaluator=None, mcp_integration=None, use_mcp=True):
    jira_issue_port = FallbackJiraIssueAdapter(...)
    confluence_page_port = FallbackConfluencePageAdapter(...)
    jira_evaluation_port = JiraEvaluationAdapter(jira_evaluator) if jira_evaluator else None
    workflow_service = RequirementWorkflowService(
        llm_provider=llm_provider,
        jira_issue_port=jira_issue_port,
        jira_evaluation_port=jira_evaluation_port,
        confluence_page_port=confluence_page_port,
    )
    return {"jira_issue_port": jira_issue_port, "confluence_page_port": confluence_page_port, "workflow_service": workflow_service}
```

- [ ] **Step 2: Switch `Chatbot` to build the workflow service through composition instead of constructing it inline**

```python
services = build_application_services(...)
self.requirement_workflow_service = services["workflow_service"]
```

- [ ] **Step 3: Switch `ChatbotAgent` to store the new ports and stop assembling fallback policy inside node handlers**

```python
self.jira_issue_port = services["jira_issue_port"]
self.confluence_page_port = services["confluence_page_port"]
```

- [ ] **Step 4: Keep agent helper functions for formatting and normalization only**

```python
success_outcome = build_jira_success_outcome(...)
failure_outcome = build_confluence_failure_outcome(...)
```

- [ ] **Step 5: Run the composition smoke tests**

Run: `pytest tests/unit/test_runtime_composition.py -q`
Expected: PASS

### Task 6: Remove Straightforward `sys.path` Workarounds and Verify the Phase

**Files:**
- Modify: `src/chatbot.py`
- Modify: `src/agent/agent_graph.py`
- Modify: `app.py`

- [ ] **Step 1: Remove the local `sys.path.insert(...)` shims where package imports already resolve**

```python
# Delete project_root / sys.path.insert setup blocks from package modules
```

- [ ] **Step 2: Run focused Phase 3a regression tests**

Run: `pytest tests/unit/test_jira_issue_adapter.py tests/unit/test_confluence_page_adapter.py tests/unit/test_requirement_workflow_service.py tests/unit/test_chatbot_requirement_workflow.py tests/unit/test_agent_jira_nodes.py tests/unit/test_agent_confluence_nodes.py tests/unit/test_runtime_composition.py -q`
Expected: PASS

- [ ] **Step 3: Run one agent integration smoke test**

Run: `pytest tests/integration/agent/test_agent_basic.py -q -m slow`
Expected: PASS

- [ ] **Step 4: Commit the Phase 3a refactor**

```bash
git add src/application src/adapters src/runtime src/services/requirement_workflow_service.py src/chatbot.py src/agent/agent_graph.py tests/unit/test_jira_issue_adapter.py tests/unit/test_confluence_page_adapter.py tests/unit/test_runtime_composition.py tests/unit/test_requirement_workflow_service.py docs/superpowers/plans/2026-04-10-phase-3a-architecture-cleanup.md
git commit -m "refactor: add phase 3a ports adapters and composition"
```
