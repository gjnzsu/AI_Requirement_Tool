# Direct Confluence Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class direct `confluence_creation` route that can create a Confluence page from freeform user input without requiring the full requirement SDLC workflow.

**Architecture:** Keep `RequirementSdlcAgent` as the guided multi-step workflow. Add a small standalone Confluence creation service for freeform page drafting + page creation, then wire that service into keyword routing, LLM intent detection, and the LangGraph branch table so direct Confluence requests bypass Jira/evaluation.

**Tech Stack:** Python, LangGraph, LangChain message models, existing Confluence adapters/ports, pytest

---

### Task 1: Add direct Confluence intent coverage

**Files:**
- Modify: `src/agent/intent_routing.py`
- Modify: `src/services/agent_intent_service.py`
- Modify: `src/services/intent_detector.py`
- Test: `tests/unit/test_agent_intent_service.py`
- Test: `tests/unit/test_intent_detector.py`

- [ ] **Step 1: Write failing tests for direct Confluence intent**
- [ ] **Step 2: Run targeted tests and confirm they fail for missing `confluence_creation` support**
- [ ] **Step 3: Add keyword, route, and LLM intent support for `confluence_creation`**
- [ ] **Step 4: Re-run targeted tests and confirm they pass**

### Task 2: Add standalone freeform Confluence creation service

**Files:**
- Create: `src/services/confluence_creation_service.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/test_confluence_creation_service.py`

- [ ] **Step 1: Write failing service tests for draft generation and page creation delegation**
- [ ] **Step 2: Run targeted service tests and confirm they fail because the service does not exist yet**
- [ ] **Step 3: Implement the minimal standalone service using the existing Confluence port**
- [ ] **Step 4: Re-run targeted service tests and confirm they pass**

### Task 3: Wire direct Confluence creation into the agent graph

**Files:**
- Modify: `src/agent/graph_builder.py`
- Modify: `src/agent/agent_graph.py`
- Test: `tests/unit/test_agent_graph_builder.py`
- Test: `tests/unit/test_agent_lifecycle_delegation.py`

- [ ] **Step 1: Write failing graph/agent tests for direct `confluence_creation` routing and handling**
- [ ] **Step 2: Run targeted tests and confirm they fail with current Jira-only Confluence flow**
- [ ] **Step 3: Inject the standalone service into `ChatbotAgent` and support direct Confluence page creation**
- [ ] **Step 4: Re-run targeted tests and confirm they pass**

### Task 4: Verify the refactor

**Files:**
- Modify: `README.md` (only if intent list or architecture text needs a small follow-up update)
- Test: `tests/unit/test_agent_intent_service.py`
- Test: `tests/unit/test_intent_detector.py`
- Test: `tests/unit/test_confluence_creation_service.py`
- Test: `tests/unit/test_agent_graph_builder.py`
- Test: `tests/unit/test_agent_lifecycle_delegation.py`

- [ ] **Step 1: Run the focused pytest command for the changed unit tests**
- [ ] **Step 2: Fix any regressions discovered during verification**
- [ ] **Step 3: Re-run the focused pytest command and confirm green output**
