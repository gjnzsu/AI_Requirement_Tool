# Metrics Instrumentation Review (Final Polish)

Date: 2026-04-13
Scope reviewed:
- `app.py` (Flask app metrics + LLM counters)
- `src/gateway/middleware/metrics.py` (in-memory gateway metrics)
- `src/gateway/gateway_service.py` (`/v1/metrics` exposure)
- `src/agent/callbacks.py` (LLM callback monitoring)

## 1) Current Strengths

- Prometheus integration is already present in Flask app:
  - HTTP request count (`http_requests_total`)
  - HTTP latency histogram (`http_request_duration_seconds`)
  - LLM tokens (`llm_tokens_total`)
  - LLM estimated cost (`llm_token_cost_usd_total`)
  - LLM error count (`llm_errors_total`)
- Gateway service exposes operational metrics on `/v1/metrics` with provider-level counters and latency.
- Gateway metrics collector uses a thread lock and bounded latency history per provider.
- Agent callback layer tracks call duration, token usage, and failures without breaking runtime flow.

## 2) Gaps / Risks (Prioritized)

### High Priority

1. Provider error attribution may be inaccurate in Flask app error path.
- Current behavior increments `llm_errors_total{provider=Config.LLM_PROVIDER}`.
- Risk: if request-level `model` differs from configured default provider, error is attributed to the wrong provider.
- Recommendation: record error metric using request-selected `model` when available.

### Medium Priority

2. Two parallel observability paths are not unified.
- Prometheus counters live in `app.py`, while gateway metrics are in-memory JSON via `/v1/metrics`.
- Risk: split dashboards and inconsistent SLO reporting across app/gateway deployments.
- Recommendation: standardize on one canonical metric backend (prefer Prometheus exposition in both paths).

3. Cost estimation logic diverges across modules.
- `app.py` uses centralized `calculate_cost(...)` based on provider/model usage.
- `src/agent/callbacks.py` uses static approximate prices.
- Risk: inconsistent cost numbers between logs and Prometheus.
- Recommendation: callback should optionally reuse centralized cost-tracker or label itself as approximate-only in emitted fields.

### Low Priority

4. No release-level metric contract document.
- Risk: future refactors can silently rename labels/metrics and break dashboards.
- Recommendation: maintain a short metric contract doc (name, type, labels, owner, alert usage).

## 3) Recommended Follow-up Actions

- [ ] Fix provider label attribution in Flask error metric path
- [ ] Add smoke test asserting expected metric series appear after one chat request
- [ ] Decide canonical metric source for dashboards (Flask `/metrics` vs gateway `/v1/metrics`)
- [ ] Align cost estimation method between callback and app-level metrics
- [ ] Publish metric contract doc in `docs/features/agent/` or `docs/architecture/`

## 4) Suggested Acceptance Criteria for Observability

- [ ] A single chat request increments HTTP + LLM token metrics with expected labels
- [ ] Forced provider failure increments the correct provider error label
- [ ] Dashboard panel queries resolve against current metric names without manual patching
- [ ] No metric-name/label changes are shipped without changelog note

## 5) Overall Assessment

Status: Good baseline in place, safe to release with moderate observability debt.

Confidence: Medium-high. Core instrumentation exists and is usable, but provider attribution accuracy and telemetry unification should be closed in the next hardening pass.
