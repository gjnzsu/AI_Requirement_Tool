# Post-Migration Hardening Checklist (Flask -> FastAPI)

Date: 2026-04-14
Owner: Backend Team
Scope: Production hardening after FastAPI migration completion

## How To Use

- Mark each item as `Done` only after objective evidence is attached.
- Record owner and due date before execution.
- Keep this checklist tied to release readiness and rollback safety.

## 1. Runtime Mode Control

- [ ] Confirm `USE_FASTAPI_BACKEND` default is safe for current rollout stage.
- [ ] Verify rollback drill: set `USE_FASTAPI_BACKEND=false`, redeploy, run smoke tests.
- [ ] Ensure rollback can be completed within one release cycle.

Evidence:
- Deployment diff or env snapshot
- Rollback drill logs
- Smoke test outputs

## 2. API Contract Lock

- [ ] Freeze critical endpoint response contracts (`/api/auth/*`, `/api/chat`, `/api/conversations*`, `/api/health`, `/metrics`).
- [ ] Enforce no-breaking-change validation in CI for contract-sensitive endpoints.
- [ ] Document approved exceptions and migration notes for any intentional contract changes.

Evidence:
- Contract test reports
- CI job links
- Change log entries

## 3. Observability Parity

- [ ] Confirm FastAPI dashboards include request rate, p95 latency, 4xx/5xx, auth failure rate.
- [ ] Validate `/metrics` exposure behavior in target environments.
- [ ] Add alerts for auth error spikes and chat endpoint regression.

Evidence:
- Dashboard screenshots/links
- Alert rule definitions
- Incident simulation output (if available)

## 4. Performance Baseline

- [ ] Run load tests for `/api/chat` and `/api/conversations`.
- [ ] Compare FastAPI vs Flask baseline for latency, error rate, and resource usage.
- [ ] Capture acceptance thresholds and pass/fail outcome.

Evidence:
- Load test report
- Baseline comparison table
- Capacity notes

## 5. Security And Middleware Validation

- [ ] Re-verify CORS, auth middleware behavior, and token handling parity.
- [ ] Ensure `BYPASS_AUTH` remains test-only and cannot be enabled unintentionally in production.
- [ ] Confirm error payloads do not expose sensitive internals in production mode.

Evidence:
- Security review notes
- Env var policy/config
- API response samples

## 6. CI/CD Reliability Gates

- [ ] Keep Flask and FastAPI integration suites in CI until cutover confidence target is met.
- [ ] Enforce `FASTAPI_PARITY_STRICT=true` in CI release paths.
- [ ] Add post-deploy smoke checks for health/auth/chat/conversations/metrics.

Evidence:
- CI workflow run URLs
- Pipeline config diff
- Post-deploy check logs

## 7. Ops Runbook Readiness

- [ ] Publish one-page runbook: cutover, rollback, incident triage.
- [ ] Include exact commands, owners, and escalation path.
- [ ] Verify on-call team can execute runbook steps without additional context.

Evidence:
- Runbook link
- Ownership matrix
- Dry-run notes

## 8. Technical Debt Cleanup Window

- [ ] Track migration-only shims and temporary compatibility logic.
- [ ] Define cleanup release window (for example after 1-2 stable release cycles).
- [ ] Assign owner and deadline for each cleanup item.

Evidence:
- Issue tracker links
- Cleanup milestones
- Final removal PRs

## Exit Criteria

The hardening phase is complete when:
- [ ] Combined API matrix remains green in CI for at least one full release cycle.
- [ ] Staging and production canary windows show no sustained regression in error rate or latency.
- [ ] Rollback drill is proven and documented.
- [ ] Ops + engineering signoff recorded.
