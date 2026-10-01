# Shared gateway deployment validation

`ai-tool-service` is ClusterIP. Runtime health checks use the shared gateway's
configured route hostname, not a Service LoadBalancer IP. Using the hostname
preserves gateway Host routing and HTTPS behavior.

For a future, explicitly authorized cloud start/deployment, supply
`-BaseUrl https://requirement.example.com` to `scripts/start-gcp-runtime.ps1` or
`scripts/deploy-gcp-runtime.ps1`, or set `AI_TOOL_BASE_URL`. The parameter takes
precedence over the environment. Supply an HTTP(S) origin only, with an optional
port/trailing slash; credentials, paths, queries, and fragments are rejected
before cloud commands run. `-SkipHealthCheck` permits omission of the URL and
still retains rollout and service endpoint checks. It does not prevent startup
or deployment.

CD remains manual (`workflow_dispatch`) and requires the `base_url` input.
Health, login, and chat smoke requests all use that origin. Resolve the current
hostname from the platform gateway route configuration before running; no
historical nip.io hostname is assumed to be live.

For the stopped POC, run only the offline regression check:

```powershell
pwsh -NoProfile -File scripts/test-runtime-validation.ps1
python scripts/test_gateway_workflow.py -v
```

The test parses scripts, mocks HTTP responses, and checks workflow contracts.
It does not start cloud resources or contact the application. Do not invoke
start/deploy scripts or dispatch CI/CD just to validate this migration: CI can
publish a cloud image, and CD deploys workloads and makes an LLM smoke request.
