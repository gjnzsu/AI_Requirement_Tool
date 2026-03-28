# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Set required env var, then start the server
# Copy .env and fill in ANTHROPIC_API_KEY
python main.py
```

The server runs on port `5000` by default (configurable via `PORT` in `.env`).

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `PORT` | `5000` | HTTP port |
| `CLAUDE_MODEL` | `claude-opus-4-5` | Claude model ID used for analysis |
| `DEBUG` | `False` | Flask debug mode |

## Architecture

This is a single-file Flask backend + vanilla JS frontend with no build step.

### Backend (`main.py`)

Flask app with three API endpoints:

- `POST /api/analyze` — accepts `{ text, language }`, sends a structured prompt to the Claude API, returns a JSON object with analysis sections: `actors`, `use_cases`, `functional_requirements`, `non_functional_requirements`, `constraints`, `assumptions`, `risks`.
- `POST /api/export` — accepts `{ data, format }` where format is `json`, `csv`, or `markdown`; returns the requirements data serialized in that format.
- `GET /api/health` — liveness check.

All static files are served from `static/` via Flask's `send_from_directory`.

### Frontend (`static/`)

No framework, no bundler. Bootstrap 5 + custom CSS + vanilla JS.

- `static/index.html` — single HTML page; includes all CSS/JS.
- `static/js/app.js` — all frontend logic: form handling, fetch calls to `/api/analyze` and `/api/export`, and DOM rendering of the structured analysis result.
- `static/css/` — custom styles layered on top of Bootstrap.

### Data Flow

1. User pastes requirements text into the textarea and selects a language (English/Chinese).
2. Frontend POSTs to `/api/analyze`.
3. Backend builds a detailed system prompt instructing Claude to extract structured requirements, calls the Anthropic API, parses the JSON response.
4. Frontend receives the JSON and renders each section (actors, use cases, functional/non-functional requirements, constraints, assumptions, risks) as collapsible cards.
5. User can export the analysis via `/api/export`.

## Post-Deployment Log & Test Checks

When asked to **"triage logs"**, **"check test status"**, **"post deployment check"**, or **"verify deployment"**, run the following checks in order and return a structured report.

### Stack Context
- Deployments: `ai-tool`, `grafana`, `prometheus`
- App service: `ai-tool-service` (LoadBalancer, port 80 → pod 5000), external IP `34.133.164.110`
- Grafana: external IP `136.114.77.0` (port 80)
- Prometheus: internal `prometheus-service:9090`

### Checklist

1. **Pod & Deployment Health**
   ```bash
   kubectl get pods
   kubectl get deployments
   ```
   Flag any pod not `1/1 Running` or with non-zero restarts.

2. **Application Logs** — scan for errors
   ```bash
   kubectl logs -l app=ai-tool --tail=50
   ```
   Search for: `ERROR`, `Exception`, `Traceback`, `CRITICAL`, `500`. Report exact line and timestamp.

3. **Prometheus Scrape Health**
   ```bash
   kubectl exec deploy/prometheus -- wget -qO- http://localhost:9090/api/v1/targets
   ```
   Confirm `health: "up"` for `ai-tool` target. Report `lastError` if down.

4. **Live Metric Verification**
   ```bash
   kubectl exec deploy/prometheus -- wget -qO- 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[2m])'
   ```
   Confirm non-empty result. Report current request rate per endpoint.

5. **Grafana Provisioning**
   ```bash
   kubectl logs -l app=grafana --tail=30
   ```
   Confirm `"provisioned dashboard is up to date"` for `ai-tool.json`. Flag any `level=error`.

6. **Culprit Commit Analysis** (only if errors found in steps 2–5)
   ```bash
   git log --oneline -10
   ```
   Cross-reference error timestamps against recent commits.

### Report Format
```
## Post-Deployment Health Report
**Pods**: [OK / ISSUES: <details>]
**App Logs**: [Clean / ERRORS: <file:line> <message>]
**Prometheus Scrape**: [UP / DOWN: <lastError>]
**Live Metrics**: [Data present / No data: <reason>]
**Grafana**: [OK / ISSUES: <details>]
**Culprit Commit** (if errors): [hash] - <message>
**Verdict**: HEALTHY / NEEDS ATTENTION
```
If all green, a one-liner "All systems healthy" is sufficient.
