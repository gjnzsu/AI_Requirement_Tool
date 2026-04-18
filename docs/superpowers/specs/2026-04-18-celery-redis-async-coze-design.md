# Async Coze Execution with Celery + Redis

## Background and Problem

The current chat API is synchronous. This works well for normal chat, RAG, Jira creation, direct Confluence creation, and Requirement SDLC drafting turns, but it becomes a poor fit for long-running agent paths such as `coze_agent`. In practice, Coze requests can take around 3 minutes to complete. That creates a poor user experience, increases the risk of request timeout or proxy-layer interruption, and makes the web request lifecycle do work it should not own directly.

The goal of this design is to move only the slow Coze path into asynchronous execution while preserving the current synchronous architecture for the rest of the product. The existing Flask API remains the entrypoint, and Celery + Redis provide the minimal async backbone needed for long-running tasks.

## Goals and Non-Goals

### Goals

- Improve UX for long-running agent requests, especially `coze_agent`, by avoiding multi-minute blocking chat requests.
- Keep the current synchronous behavior unchanged for existing fast routes such as general chat, RAG, Jira creation, Confluence creation, and Requirement SDLC draft turns.
- Introduce a minimal async execution model that fits the current Flask architecture and can be extended later.
- Use Redis-backed Celery jobs to provide clear request lifecycle states for slow tasks: `queued`, `running`, `completed`, and `failed`.
- Return enough result metadata for the frontend and troubleshooting without expanding scope into a full job-management platform.

### Non-Goals

- Do not migrate the backend from Flask to FastAPI in this phase.
- Do not introduce SSE, WebSockets, or streaming updates in v1.
- Do not add durable job persistence outside Redis in v1.
- Do not make all chat routes asynchronous; only the slow Coze path is in scope initially.
- Do not add cancellation, retry controls, or user-visible progress text in v1.

### Example Success Criteria

- A Coze request no longer keeps the `/api/chat` HTTP request open for multiple minutes.
- A Coze request returns `202 Accepted` with a `job_id` and can be completed asynchronously through polling.
- Existing non-Coze chat flows continue to return synchronous `200` responses without behavior regression.
- The frontend can poll job status and render the final response when the Celery task completes.
- A failed Coze job returns a clear `failed` status and error payload instead of leaving the request hanging or timing out.

## Proposed Architecture

The system will keep the existing Flask API as the request entrypoint and introduce Celery + Redis only for long-running Coze requests. `POST /api/chat` remains the single chat endpoint. For normal routes, it continues to return a synchronous `200` response. When the request is detected as `coze_agent`, the API returns `202 Accepted` with a `job_id`, and the actual Coze execution is delegated to a Celery worker.

Redis will serve both as the Celery broker and result backend in phase 1. A small application-level wrapper service will sit between Flask and Celery so the web layer does not depend directly on Celery task internals. That wrapper will be responsible for creating the job, submitting it to a shared queue, and normalizing the job-status/result payload returned to the frontend. The worker will receive the captured conversation context at enqueue time, execute the existing Coze logic through a small service wrapper, and write the final result back to Redis via Celery’s result backend.

The first version will support coarse job states only: `queued`, `running`, `completed`, and `failed`. The completed result should contain the final assistant response plus lightweight metadata such as timestamps and failure details when relevant. No retry, cancellation, or progress text is included in v1. This keeps the design small, but leaves a clear extension path for future async routes and richer job controls.

## API Contract

The existing `POST /api/chat` endpoint will remain the single entrypoint for chat requests. The request body will not change between synchronous and asynchronous flows. Requests that resolve to normal fast paths will continue to return the current synchronous `200 OK` response shape. Requests that resolve to `coze_agent` will return `202 Accepted` and a minimal async acknowledgment payload.

### `POST /api/chat`

- Request body: unchanged from the current chat API.
- Synchronous response: unchanged current `200 OK` contract.
- Asynchronous Coze response: `202 Accepted`

Example async response:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

The API contract intentionally keeps this response minimal for v1. The frontend will use the returned `job_id` to poll for status and final result.

### `GET /api/jobs/{job_id}`

- Purpose: return the current state and final result of an async Coze job.
- Authentication: same auth token requirements as existing chat APIs.
- Response states:
  - `queued`
  - `running`
  - `completed`
  - `failed`

Example running response:

```json
{
  "job_id": "uuid",
  "status": "running"
}
```

Example completed response:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "result": {
    "response": "final assistant message",
    "conversation_id": "conv-123",
    "agent_mode": "auto",
    "ui_actions": [],
    "workflow_progress": null,
    "timestamp": "2026-04-18T12:34:56"
  }
}
```

Example failed response:

```json
{
  "job_id": "uuid",
  "status": "failed",
  "error": "Coze request failed or timed out"
}
```

Where possible, the completed job result should match the existing normal chat response shape so the frontend can reuse current rendering behavior with minimal branching. No additional endpoint such as `GET /api/conversations/{id}/jobs` is included in v1.

## Redis and Celery Design

Phase 1 will use a single Redis connection source, provided through one environment variable such as `REDIS_URL`. That value will be used for both the Celery broker and the Celery result backend. This keeps configuration small and avoids introducing separate connection management before it is needed.

Celery will run with a single shared queue and one worker deployment using general-purpose settings. No queue partitioning or worker autoscaling is required in v1. The first async workload is `coze_agent` only, but the queue/task structure should remain generic enough to support additional slow routes later.

Task payloads should contain only the captured conversation snapshot and request metadata needed to execute the job deterministically. This includes the original user message, recent conversation context, conversation identifier, selected model or provider context if relevant, and agent mode. Raw auth tokens or broader user session state should not be passed into the task payload.

Job results will live only in Redis through Celery’s result backend in v1. Results should expire automatically with a default TTL of 24 hours so Redis does not accumulate stale job records indefinitely. Since this phase does not add durable persistence outside Redis, expiration is an expected lifecycle behavior.

The Coze task should also have a hard Celery timeout to prevent workers from hanging indefinitely. Since the current Coze timeout is already configured at 300 seconds, the Celery task timeout will match that value in phase 1. If the task exceeds the timeout or fails, Celery should mark the job as failed and the API should surface a user-safe error string through the polling endpoint.

## Flask Integration

The Flask route layer should remain thin. The decision to execute synchronously or enqueue an async job should live in the existing runtime/service orchestration layer rather than directly inside `app.py`. This keeps request parsing and HTTP response formatting separate from execution strategy and makes it easier to extend async behavior later without growing route complexity.

The async decision should be driven by the normal intent-routing path. After the request is parsed and conversation setup is completed, the runtime layer should determine whether the request resolves to `coze_agent`. If it does, the runtime should enqueue a Celery job instead of waiting for a synchronous response. All other intents should continue through the current synchronous execution path with no behavioral change.

When an async Coze request is accepted, the conversation record should be created immediately before returning `202 Accepted`. This ensures the frontend already has a stable conversation identifier and can continue rendering the interaction in the same chat thread. Once the Celery task completes, the final assistant message should be written back into the same conversation history automatically so async and sync conversations remain consistent from the user’s perspective.

The worker should not boot the full chat stack unless necessary. Instead, it should call a small Coze-focused application wrapper that reuses the existing Coze service logic while minimizing unnecessary initialization and reducing coupling to the broader synchronous request lifecycle. This keeps the worker path smaller, easier to test, and better isolated from unrelated chat behaviors.

The job lookup endpoint should return `404 Not Found` when a `job_id` does not exist or has already expired from Redis, rather than synthesizing a failed job payload. This gives the API a cleaner contract and makes missing-job behavior explicit.

## Frontend Polling Flow

The first version should keep the UI model as close as possible to the current chat experience. When `POST /api/chat` returns a normal synchronous `200` response, the frontend should behave exactly as it does today. When the endpoint returns `202 Accepted` for an async Coze request, the frontend should immediately insert a placeholder assistant message into the current chat thread, such as “Processing your request...”.

The frontend should then begin polling `GET /api/jobs/{job_id}` every 3 seconds. No separate job-status panel is needed in v1. The async state should remain embedded in the normal chat experience so users do not need to learn a second interaction model for slow requests.

When the polled job reaches `completed`, the placeholder message should be replaced in place with the final assistant response returned from the job result. This keeps the transcript clean and makes the async flow feel consistent with synchronous chat behavior. If the job reaches `failed`, the placeholder should be replaced with a user-safe error message in the same chat thread.

Polling should continue until one of four terminal outcomes is reached: `completed`, `failed`, `404 not found`, or an explicit client-side stop caused by navigation away from the page. No refresh recovery behavior is required in v1. If the page is refreshed while a job is still running, the job may continue in Redis/Celery, but the initial implementation does not need to reattach the UI to in-flight jobs after reload.

## Deployment on GKE

The first version should deploy Redis inside the same GKE cluster as the existing Flask application. This keeps infrastructure simple and avoids introducing a second platform dependency before the async flow has been validated. The design should still treat managed Redis as a valid future replacement, but it is not required for v1.

Celery should run as a separate Kubernetes deployment from the Flask web application. The web deployment remains responsible for receiving chat requests, enqueueing async jobs, and serving job-status polling endpoints. The worker deployment is responsible only for consuming Celery tasks and executing long-running Coze jobs. This separation provides clearer operational boundaries and avoids tying slow task execution to web pod lifecycle or request-serving capacity.

The Flask app and Celery worker should use the same container image in v1, with different startup commands or entrypoints. This keeps CI/CD simple, ensures web and worker code stay version-aligned, and avoids maintaining separate images for the same codebase.

Redis persistence should be considered optional for phase 1. Since job state and results are intentionally short-lived and Redis is being used only as broker and result backend, durable Redis storage is not required to meet the initial goals. If Redis restarts, in-flight jobs or completed results may be lost, which is acceptable for the first release.

The deployment notes should include basic operational expectations:

- the web deployment depends on Redis availability to enqueue and query async jobs
- the worker deployment depends on Redis availability to consume tasks and write results
- readiness should confirm process startup and configuration validity
- autoscaling for worker throughput should be treated as future work, not part of v1

The expected GKE shape for phase 1 is:

```text
GKE Cluster
  - Flask web deployment
  - Celery worker deployment
  - Redis deployment + service
```

## Risks and Future Extensions

The main risks in this design are a mix of reliability, UX limitations, and operational complexity, even though the first version keeps scope intentionally small.

### Key Risks

- **Redis-backed job state is not durable in v1.** If Redis restarts or results expire, job state may be lost.
- **Expired jobs will return `404 Not Found`.** This is expected behavior in phase 1 because job results live only in Redis with a TTL.
- **Page refresh loses in-flight UI tracking.** A running job may continue successfully in Celery, but the first version does not restore polling state automatically after the user reloads the page.
- **Web and worker coordination adds operational complexity.** Even with a small setup, the system now depends on correct configuration across Flask, Celery, Redis, and Kubernetes deployments.
- **Conversation consistency must be handled carefully.** Since async completion writes results back after the original request has returned, the implementation must ensure the final assistant message is appended to the correct conversation reliably.

### Future Extensions

- **Retry support** for failed Coze jobs, first at the worker level and later potentially from the UI.
- **Additional async agents** beyond `coze_agent` if other long-running routes begin to show the same UX problem.
- **Refresh recovery** so the frontend can reconnect to in-flight jobs after page reload.
- **Richer delivery mechanisms** such as SSE or WebSocket updates if polling becomes limiting.
- **Durable job persistence** outside Redis if retention, auditing, or stronger recovery guarantees become necessary.
- **Managed Redis** if the in-cluster Redis deployment becomes an operational burden or reliability concern.

This phase intentionally accepts a few limitations in exchange for a smaller and safer first async rollout. The design is successful if it removes multi-minute blocking requests for Coze while preserving the current synchronous experience for the rest of the product.
