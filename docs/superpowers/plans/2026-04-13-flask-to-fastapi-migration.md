# Flask To FastAPI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the current Flask backend to a FastAPI-first backend with zero API contract regressions and controlled rollback at every phase.

**Architecture:** Use a strangler migration. Keep Flask stable while introducing FastAPI application modules that reuse existing runtime/services, then switch traffic endpoint-group by endpoint-group behind a feature flag and parity tests. Preserve current response shapes and auth semantics during migration.

**Tech Stack:** FastAPI, Uvicorn, Pydantic, existing `src/webapp/runtime.py`, existing services (`src/chatbot.py`, `src/services/*`), pytest (unit/integration/e2e)

---

## Scope And Guardrails

- In scope:
  - API backend migration from Flask routes to FastAPI routes.
  - Auth/chat/conversations/search/current-model/health endpoint parity.
  - Runtime reuse (`AppRuntime`) and service reuse (no business-logic rewrite).
  - Observability parity (`/metrics`, error handling, status codes).
- Out of scope (this plan):
  - Frontend redesign.
  - Database schema redesign.
  - LLM provider logic redesign.
  - Full deprecation/removal of Flask until parity and cutover complete.

## Files Map (Planned)

**Create**
- `src/fastapi_app/__init__.py`
- `src/fastapi_app/app.py`
- `src/fastapi_app/dependencies.py`
- `src/fastapi_app/models.py`
- `src/fastapi_app/routes/auth.py`
- `src/fastapi_app/routes/chat.py`
- `src/fastapi_app/routes/conversations.py`
- `src/fastapi_app/routes/system.py`
- `tests/integration/api_fastapi/test_auth_api_fastapi.py`
- `tests/integration/api_fastapi/test_chat_api_fastapi.py`
- `tests/integration/api_fastapi/test_conversations_api_fastapi.py`
- `tests/integration/api_fastapi/test_system_api_fastapi.py`
- `tests/integration/api_fastapi/test_error_contract_fastapi.py`
- `docs/architecture/fastapi-migration-notes.md`

**Modify**
- `src/webapp/runtime.py` (dependency-friendly adapters if needed; no behavior change)
- `config/config.py` (feature flags for migration)
- `README.md` (run instructions + migration status)
- `.github/workflows/ci.yml` (add FastAPI parity test stage)
- `k8s/deployment.yaml` (entrypoint toggle after cutover phase)

---

### Task 1: Baseline Contract Freeze

**Files:**
- Modify: `docs/architecture/fastapi-migration-notes.md` (create if missing)
- Test: `tests/integration/api/` (existing suite used as baseline)

- [ ] **Step 1: Capture current Flask endpoint inventory and response contracts**

Run:
```bash
python -m pytest tests/integration/api/ -q
```
Expected: Existing API integration suite green (or known failures documented).

- [ ] **Step 2: Record contract table in migration notes**

Include exact endpoints and required status/shape:
- `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- `/api/chat`, `/api/current-model`
- `/api/conversations*`, `/api/new-chat`, `/api/search`
- `/api/health`, `/metrics`

- [ ] **Step 3: Commit baseline docs**

```bash
git add docs/architecture/fastapi-migration-notes.md
git commit -m "docs: freeze current flask api contract for fastapi migration"
```

### Task 2: Create FastAPI App Skeleton Reusing Runtime

**Files:**
- Create: `src/fastapi_app/app.py`, `src/fastapi_app/dependencies.py`, `src/fastapi_app/__init__.py`
- Modify: `src/webapp/runtime.py` (only if small helper export needed)
- Test: `tests/integration/api_fastapi/test_system_api_fastapi.py`

- [ ] **Step 1: Write failing system tests for FastAPI health and bootstrapping**

Tests must assert:
- `GET /api/health` returns status 200 and `{"status": "ok"}`
- app boot does not instantiate duplicate runtime state per request

- [ ] **Step 2: Implement `create_fastapi_app()` with shared runtime initialization**

Requirements:
- Instantiate and store `AppRuntime` once at startup.
- Provide dependency getter for runtime.
- Add CORS equivalent to current Flask setup.

- [ ] **Step 3: Run new system tests**

```bash
python -m pytest tests/integration/api_fastapi/test_system_api_fastapi.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/fastapi_app src/webapp/runtime.py tests/integration/api_fastapi/test_system_api_fastapi.py
git commit -m "feat: add fastapi app skeleton with shared appruntime"
```

### Task 3: Migrate Auth Endpoints With Contract Parity

**Files:**
- Create: `src/fastapi_app/routes/auth.py`, `src/fastapi_app/models.py`
- Test: `tests/integration/api_fastapi/test_auth_api_fastapi.py`

- [ ] **Step 1: Write failing auth parity tests**

Cover:
- login success/failure
- logout requires token
- `/api/auth/me` semantics
- error payload keys match Flask (`error`, optional `message`)

- [ ] **Step 2: Implement FastAPI auth routes using existing auth services from runtime dependency**

Rules:
- Preserve response shape and status codes.
- Keep JWT behavior delegated to existing `src/auth/*`.

- [ ] **Step 3: Run auth parity tests**

```bash
python -m pytest tests/integration/api_fastapi/test_auth_api_fastapi.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/fastapi_app/routes/auth.py src/fastapi_app/models.py tests/integration/api_fastapi/test_auth_api_fastapi.py
git commit -m "feat: migrate auth endpoints to fastapi with contract parity"
```

### Task 4: Migrate Chat + Current Model Endpoints

**Files:**
- Create: `src/fastapi_app/routes/chat.py`
- Test: `tests/integration/api_fastapi/test_chat_api_fastapi.py`

- [ ] **Step 1: Write failing chat parity tests**

Cover:
- `/api/chat` happy path
- invalid JSON / invalid model / invalid agent_mode
- rate-limit and internal error mapping
- `/api/current-model`

- [ ] **Step 2: Implement chat routes using `AppRuntime.execute_chat_request()`**

Rules:
- Preserve payload keys: `response`, `conversation_id`, `agent_mode`, `ui_actions`, `workflow_progress`, `timestamp`.
- Preserve status code behavior and token-required enforcement.

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/integration/api_fastapi/test_chat_api_fastapi.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/fastapi_app/routes/chat.py tests/integration/api_fastapi/test_chat_api_fastapi.py
git commit -m "feat: migrate chat and model endpoints to fastapi"
```

### Task 5: Migrate Conversation/Search Endpoints

**Files:**
- Create: `src/fastapi_app/routes/conversations.py`
- Test: `tests/integration/api_fastapi/test_conversations_api_fastapi.py`

- [ ] **Step 1: Write failing conversation parity tests**

Cover:
- list/get/delete/clear/update-title/new-chat/search
- memory-manager and in-memory fallback behaviors
- not-found and validation errors

- [ ] **Step 2: Implement FastAPI conversation routes by reusing current logic paths**

Rules:
- Preserve existing response body fields and error semantics.
- Keep route paths identical.

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/integration/api_fastapi/test_conversations_api_fastapi.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/fastapi_app/routes/conversations.py tests/integration/api_fastapi/test_conversations_api_fastapi.py
git commit -m "feat: migrate conversation endpoints to fastapi"
```

### Task 6: Error And Metrics Parity

**Files:**
- Create: `src/fastapi_app/routes/system.py`
- Test: `tests/integration/api_fastapi/test_error_contract_fastapi.py`, `tests/integration/api_fastapi/test_system_api_fastapi.py`

- [ ] **Step 1: Write failing tests for error contract and metrics exposure**

Cover:
- API errors must return JSON payloads.
- `/metrics` behavior under available/unavailable Prometheus setup.

- [ ] **Step 2: Implement system/error route behavior parity**

Rules:
- Keep Flask-style JSON error contract.
- Keep operational `/metrics` endpoint availability and content-type behavior.

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/integration/api_fastapi/test_error_contract_fastapi.py tests/integration/api_fastapi/test_system_api_fastapi.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/fastapi_app/routes/system.py tests/integration/api_fastapi/test_error_contract_fastapi.py tests/integration/api_fastapi/test_system_api_fastapi.py
git commit -m "feat: align fastapi error and metrics contracts with flask"
```

### Task 7: Dual-Run And CI Gate

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `config/config.py`
- Modify: `README.md`

- [ ] **Step 1: Add migration flags**

Config flags:
- `USE_FASTAPI_BACKEND` (default `false`)
- `FASTAPI_PARITY_STRICT` (default `true` in CI)

- [ ] **Step 2: Add FastAPI integration test stage in CI**

Run both:
- existing Flask integration API tests
- new FastAPI parity tests

- [ ] **Step 3: Update README run instructions**

Add:
- Flask run command (current stable)
- FastAPI run command (migration path)
- parity-test commands

- [ ] **Step 4: Run full API test matrix locally**

```bash
python -m pytest tests/integration/api/ tests/integration/api_fastapi/ -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml config/config.py README.md
git commit -m "ci: add fastapi parity gates and migration flags"
```

### Task 8: Traffic Cutover And Rollback Safety

**Files:**
- Modify: `k8s/deployment.yaml`
- Modify: `docs/architecture/fastapi-migration-notes.md`

- [ ] **Step 1: Define cutover checklist in docs**

Checklist must include:
- parity tests green
- smoke tests green (`/api/health`, login, chat, conversations, `/metrics`)
- error-rate and latency SLO compare window

- [ ] **Step 2: Deploy FastAPI behind flag to staging**

Verify:
- endpoint parity
- auth and chat state behavior
- no regression in workflow progress payloads

- [ ] **Step 3: Controlled production cutover**

Switch deployment command/entrypoint only after staging pass.

- [ ] **Step 4: Rollback rule**

If any P1 regression in auth/chat/conversations/metrics, revert flag and deployment to Flask path within one release cycle.

- [ ] **Step 5: Commit deployment/docs updates**

```bash
git add k8s/deployment.yaml docs/architecture/fastapi-migration-notes.md
git commit -m "ops: add fastapi cutover and rollback controls"
```

---

## Verification Matrix (Must Pass Before Full Migration)

- [ ] `python -m pytest tests/unit/ -v`
- [ ] `python -m pytest tests/integration/api/ -v`
- [ ] `python -m pytest tests/integration/api_fastapi/ -v`
- [ ] `python -m pytest tests/e2e/ -m e2e_integration -v`
- [ ] Staging smoke for login/chat/conversations/metrics
- [ ] Production canary window with no elevated error rate

## Delivery Milestones

1. **M1 - Scaffold + Auth parity** (Tasks 1-3)
2. **M2 - Chat + Conversation parity** (Tasks 4-5)
3. **M3 - Metrics/error parity + CI gates** (Tasks 6-7)
4. **M4 - Controlled cutover** (Task 8)

## Recommendation

Proceed now with migration **only as phased strangler migration**. Do not perform big-bang Flask removal until M4 is complete and rollback drills are validated.
