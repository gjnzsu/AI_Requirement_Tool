# Final QA Sign-off Checklist (Agent Flow Redesign)

Date: 2026-04-13
Scope: Product agent flow redesign, refactor, and UX improvements
Owner: Engineering + Product + QA

## 1) Release Gate (Must Pass)

- [ ] Smoke test login and authenticated landing page
- [ ] Send first message from a new chat and receive a valid response
- [ ] Continue existing conversation with preserved context
- [ ] Switch model (`openai`, `gemini`, `deepseek`) and verify response path
- [ ] Trigger requirement SDLC mode and verify workflow progress payload is returned
- [ ] Create/read/update/delete conversation operations succeed from UI
- [ ] Rate-limit message is user-friendly (`429`) and non-blocking for recovery path
- [ ] `/api/health` returns healthy in target environment
- [ ] `/metrics` endpoint is reachable when Prometheus dependency is enabled
- [ ] No P0/P1 regressions in auth, chat, or conversation storage

## 2) Automated Validation (Recommended Commands)

- Unit (core + gateway metrics):
  - `pytest tests/unit/test_gateway/test_metrics.py -q`
  - `pytest tests/unit/test_agent_graph_builder.py -q`
  - `pytest tests/unit/test_chat_flow_services.py -q`
- API integration (chat + auth):
  - `pytest tests/integration/api/test_chat_api.py -q`
  - `pytest tests/integration/api/test_auth_api.py -q`
- E2E UI (fast, backend-independent):
  - `pytest tests/e2e/ -m e2e_ui -n auto`
- E2E integration (full stack):
  - `pytest tests/e2e/ -m e2e_integration -n auto`

## 3) UX Regression Checklist

- [ ] Empty message guard works and gives clear feedback
- [ ] Loading state appears quickly and resolves predictably
- [ ] Error cards/messages are actionable and not leaking internals
- [ ] Conversation titles auto-update correctly after first message
- [ ] Message action buttons (copy/regenerate/etc.) work after refactor
- [ ] Sidebar search/filter behavior remains stable with many conversations
- [ ] Mobile view: no clipped panels/buttons, no horizontal overflow
- [ ] Keyboard accessibility: tab order, enter-to-submit, escape behavior

## 4) Agent Behavior Validation

- [ ] Intent routing still separates general chat vs requirement workflow cases
- [ ] Requirement workflow output includes expected `ui_actions`
- [ ] Workflow progress payload remains schema-consistent for frontend rendering
- [ ] Timeout and fallback behavior does not trap user in dead-end states
- [ ] Error path still returns safe JSON payload for `/api/*` routes

## 5) Observability Verification

- [ ] HTTP request counter increases with traffic
- [ ] Request latency histogram shows data for chat endpoints
- [ ] LLM token counters increase for prompt/completion traffic
- [ ] LLM error counter increments on forced provider failure scenario
- [ ] Dashboard queries and alert rules still match metric names/labels

## 6) Final Go/No-Go

- [ ] Product sign-off complete
- [ ] Engineering sign-off complete
- [ ] QA sign-off complete
- [ ] Rollback owner + rollback steps confirmed
- [ ] Release notes approved

## 7) Suggested Evidence to Attach

- Test report artifact links (unit/integration/e2e)
- One successful end-to-end screen recording
- `/metrics` snapshot after smoke tests
- Known issues list (if any) with severity and owner
