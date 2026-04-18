# Async Coze Execution with Celery + Redis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add async execution for `coze_agent` using Celery + Redis while keeping all existing non-Coze chat routes synchronous.

**Architecture:** Keep Flask as the only HTTP entrypoint and let the runtime layer decide whether a request stays synchronous or becomes an async Celery job. Use Redis as both Celery broker and result backend, persist the final assistant reply back into the same conversation, and expose a polling endpoint for coarse job states only.

**Tech Stack:** Flask, Celery, Redis, existing runtime/chatbot services, SQLite conversation storage via `memory_manager`, Kubernetes on GKE, pytest

---

## File Structure

**Create**
- `src/async_jobs/__init__.py`
- `src/async_jobs/celery_app.py`
- `src/async_jobs/tasks.py`
- `src/services/async_job_service.py`
- `src/services/async_coze_execution_service.py`
- `tests/unit/test_async_job_service.py`
- `tests/unit/test_async_coze_execution_service.py`
- `tests/integration/api/test_async_chat_api.py`
- `k8s/redis-deployment.yaml`
- `k8s/redis-service.yaml`
- `k8s/celery-worker-deployment.yaml`

**Modify**
- `config/config.py`
- `requirements-prod.txt`
- `requirements.txt`
- `app.py`
- `src/webapp/runtime.py`
- `src/services/__init__.py`
- `web/static/js/app.js`
- `README.md`

---

### Task 1: Add Celery and Redis Configuration

**Files:**
- Modify: `config/config.py`
- Modify: `requirements-prod.txt`
- Modify: `requirements.txt`
- Test: `tests/unit/test_async_job_service.py`

- [ ] **Step 1: Write the failing config test**

```python
from config.config import Config


def test_async_job_config_uses_single_redis_url(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis-service:6379/0")
    monkeypatch.setenv("ASYNC_COZE_ENABLED", "true")

    assert Config.REDIS_URL == "redis://redis-service:6379/0"
    assert Config.CELERY_BROKER_URL == "redis://redis-service:6379/0"
    assert Config.CELERY_RESULT_BACKEND == "redis://redis-service:6379/0"
    assert Config.CELERY_RESULT_TTL_SECONDS == 86400
    assert Config.ASYNC_COZE_ENABLED is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_async_job_service.py::test_async_job_config_uses_single_redis_url -v`

Expected: FAIL because the async config keys do not exist yet.

- [ ] **Step 3: Add config and dependencies**

Update `config/config.py` with:

```python
REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_RESULT_TTL_SECONDS: int = int(os.getenv('CELERY_RESULT_TTL_SECONDS', '86400'))
ASYNC_COZE_ENABLED: bool = os.getenv('ASYNC_COZE_ENABLED', 'true').lower() in ('true', '1', 'yes')
CELERY_TASK_TIME_LIMIT: int = int(os.getenv('CELERY_TASK_TIME_LIMIT', '300'))
```

Add to `requirements-prod.txt` and `requirements.txt`:

```text
celery[redis]>=5.4.0,<6.0.0
redis>=5.0.0,<6.0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_async_job_service.py::test_async_job_config_uses_single_redis_url -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/config.py requirements-prod.txt requirements.txt tests/unit/test_async_job_service.py
git commit -m "feat: add celery and redis configuration"
```

### Task 2: Add Celery App and Async Job Service

**Files:**
- Create: `src/async_jobs/__init__.py`
- Create: `src/async_jobs/celery_app.py`
- Create: `src/services/async_job_service.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/test_async_job_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
from unittest.mock import Mock

from src.services.async_job_service import AsyncJobService


def test_enqueue_coze_job_returns_job_id_and_queued_status():
    task = Mock()
    task.id = "job-123"
    celery_task = Mock()
    celery_task.apply_async.return_value = task

    service = AsyncJobService(celery_task=celery_task)

    result = service.enqueue_coze_job(
        payload={"message": "ai news", "conversation_id": "conv-1"}
    )

    assert result == {"job_id": "job-123", "status": "queued"}


def test_get_job_status_returns_completed_payload():
    async_result = Mock()
    async_result.state = "SUCCESS"
    async_result.result = {"response": "done", "conversation_id": "conv-1"}

    service = AsyncJobService(celery_task=Mock(), result_factory=Mock(return_value=async_result))

    result = service.get_job_status("job-123")

    assert result["job_id"] == "job-123"
    assert result["status"] == "completed"
    assert result["result"]["response"] == "done"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_async_job_service.py -v`

Expected: FAIL because the async job service does not exist yet.

- [ ] **Step 3: Implement the minimal Celery app and async job service**

Create `src/async_jobs/celery_app.py`:

```python
from celery import Celery

from config.config import Config


celery_app = Celery(
    "ai_requirement_tool",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    result_expires=Config.CELERY_RESULT_TTL_SECONDS,
    task_time_limit=Config.CELERY_TASK_TIME_LIMIT,
    task_track_started=True,
)
```

Create `src/services/async_job_service.py`:

```python
class AsyncJobService:
    def __init__(self, celery_task, result_factory=None):
        self.celery_task = celery_task
        self.result_factory = result_factory

    def enqueue_coze_job(self, payload):
        task = self.celery_task.apply_async(kwargs=payload)
        return {"job_id": task.id, "status": "queued"}

    def get_job_status(self, job_id):
        async_result = self.result_factory(job_id)
        ...
```

Map Celery states to API states:
- `PENDING` -> `queued`
- `STARTED` -> `running`
- `SUCCESS` -> `completed`
- `FAILURE` -> `failed`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_async_job_service.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/async_jobs/__init__.py src/async_jobs/celery_app.py src/services/async_job_service.py src/services/__init__.py tests/unit/test_async_job_service.py
git commit -m "feat: add celery app and async job service"
```

### Task 3: Add Coze Async Execution Wrapper and Celery Task

**Files:**
- Create: `src/services/async_coze_execution_service.py`
- Create: `src/async_jobs/tasks.py`
- Test: `tests/unit/test_async_coze_execution_service.py`

- [ ] **Step 1: Write the failing worker tests**

```python
from unittest.mock import Mock

from src.services.async_coze_execution_service import AsyncCozeExecutionService


def test_execute_writes_assistant_message_back_to_conversation():
    memory_manager = Mock()
    coze_service = Mock()
    coze_service.handle.return_value = {
        "messages": [],
        "coze_result": {"response": "AI report ready"},
        "response_text": "AI report ready",
    }

    service = AsyncCozeExecutionService(
        coze_agent_service=coze_service,
        memory_manager=memory_manager,
    )

    result = service.execute(
        user_input="give me ai news",
        conversation_id="conv-1",
        conversation_history=[],
        agent_mode="auto",
    )

    assert result["response"] == "AI report ready"
    memory_manager.add_message.assert_any_call("conv-1", "assistant", "AI report ready")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_async_coze_execution_service.py -v`

Expected: FAIL because the execution wrapper does not exist yet.

- [ ] **Step 3: Implement the wrapper service and Celery task**

Create `src/services/async_coze_execution_service.py`:

```python
from datetime import datetime


class AsyncCozeExecutionService:
    def __init__(self, coze_agent_service, memory_manager):
        self.coze_agent_service = coze_agent_service
        self.memory_manager = memory_manager

    def execute(self, *, user_input, conversation_id, conversation_history, agent_mode):
        result = self.coze_agent_service.handle(
            user_input=user_input,
            conversation_history=conversation_history,
            previous_result=None,
        )
        response_text = result.get("response_text") or result.get("response") or ""
        self.memory_manager.add_message(conversation_id, "assistant", response_text)
        return {
            "response": response_text,
            "conversation_id": conversation_id,
            "agent_mode": agent_mode,
            "ui_actions": [],
            "workflow_progress": None,
            "timestamp": datetime.now().isoformat(),
        }
```

Create `src/async_jobs/tasks.py`:

```python
from src.async_jobs.celery_app import celery_app


@celery_app.task(bind=True, name="async_jobs.execute_coze_chat")
def execute_coze_chat(self, **payload):
    service = ...
    return service.execute(**payload)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_async_coze_execution_service.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/async_coze_execution_service.py src/async_jobs/tasks.py tests/unit/test_async_coze_execution_service.py
git commit -m "feat: add async coze execution task"
```

### Task 4: Add Async Branch to Runtime and Chat API

**Files:**
- Modify: `src/webapp/runtime.py`
- Modify: `app.py`
- Test: `tests/integration/api/test_async_chat_api.py`

- [ ] **Step 1: Write the failing API tests**

```python
def test_chat_returns_202_for_coze_async_request(...):
    response = test_client.post(
        "/api/chat",
        json={"message": "ai daily news", "conversation_id": "conv-1"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["job_id"]
    assert payload["status"] == "queued"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/api/test_async_chat_api.py::test_chat_returns_202_for_coze_async_request -v`

Expected: FAIL because `/api/chat` still always blocks for a synchronous result.

- [ ] **Step 3: Implement async branching in the runtime layer**

Add to `src/webapp/runtime.py`:

```python
@dataclass
class AsyncChatRequestResult:
    conversation_id: str
    job_id: str
    status: str
```

Add a runtime method such as:

```python
def execute_async_chat_request(...):
    intent = chatbot.agent._detect_intent({...}).get("intent")
    if intent != "coze_agent":
        return None
    return async_job_service.enqueue_coze_job({...})
```

Update `app.py` so `POST /api/chat`:
- ensures conversation first
- calls runtime async check
- returns `202` + `job_id` only for Coze requests
- preserves current `200` behavior for all other routes

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/api/test_async_chat_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/webapp/runtime.py app.py tests/integration/api/test_async_chat_api.py
git commit -m "feat: enqueue coze requests asynchronously"
```

### Task 5: Add Job Polling Endpoint

**Files:**
- Modify: `app.py`
- Test: `tests/integration/api/test_async_chat_api.py`

- [ ] **Step 1: Write the failing polling endpoint tests**

```python
def test_get_job_status_returns_completed_result(...):
    response = test_client.get(
        "/api/jobs/job-123",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "completed"
    assert payload["result"]["response"] == "done"


def test_get_job_status_returns_404_for_missing_job(...):
    response = test_client.get(
        "/api/jobs/missing-job",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/api/test_async_chat_api.py::test_get_job_status_returns_completed_result tests/integration/api/test_async_chat_api.py::test_get_job_status_returns_404_for_missing_job -v`

Expected: FAIL because `/api/jobs/<job_id>` does not exist yet.

- [ ] **Step 3: Add the polling endpoint**

Add to `app.py`:

```python
@app.route('/api/jobs/<job_id>', methods=['GET'])
@token_required
def get_job_status(current_user, job_id):
    result = async_job_service.get_job_status(job_id)
    if result is None:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(result)
```

Use only:
- `job_id`
- `status`
- `result`
- `error`

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/api/test_async_chat_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/integration/api/test_async_chat_api.py
git commit -m "feat: add async job polling endpoint"
```

### Task 6: Add Frontend Polling and Placeholder Replacement

**Files:**
- Modify: `web/static/js/app.js`
- Test: `tests/integration/api/test_async_chat_api.py`

- [ ] **Step 1: Write the failing frontend-oriented API test**

```python
def test_async_chat_response_shape_is_minimal_and_pollable(...):
    response = test_client.post(
        "/api/chat",
        json={"message": "ai daily report"},
        headers={"Authorization": f"Bearer {token}"},
    )

    payload = response.get_json()
    assert sorted(payload.keys()) == ["job_id", "status"]
```

- [ ] **Step 2: Run test to verify it fails if the response shape is wrong**

Run: `pytest tests/integration/api/test_async_chat_api.py::test_async_chat_response_shape_is_minimal_and_pollable -v`

Expected: FAIL until the async response contract is finalized.

- [ ] **Step 3: Implement the frontend polling flow**

Update `web/static/js/app.js` to:

```javascript
if (response.status === 202) {
  const data = await response.json();
  const placeholderId = addMessage("assistant", "Processing your request...");
  pollJobStatus(data.job_id, placeholderId);
  return;
}
```

Add:

```javascript
async function pollJobStatus(jobId, placeholderId) {
  const intervalId = setInterval(async () => {
    const response = await auth.authenticatedFetch(`/api/jobs/${jobId}`);
    if (response.status === 404) {
      replaceMessage(placeholderId, "This async job is no longer available.");
      clearInterval(intervalId);
      return;
    }
    const data = await response.json();
    if (data.status === "completed") {
      replaceMessage(placeholderId, data.result.response);
      clearInterval(intervalId);
    } else if (data.status === "failed") {
      replaceMessage(placeholderId, data.error || "The request failed.");
      clearInterval(intervalId);
    }
  }, 3000);
}
```

- [ ] **Step 4: Run API tests to verify the response contract still passes**

Run: `pytest tests/integration/api/test_async_chat_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/static/js/app.js tests/integration/api/test_async_chat_api.py
git commit -m "feat: add frontend polling for async coze jobs"
```

### Task 7: Add GKE Redis and Worker Deployments

**Files:**
- Create: `k8s/redis-deployment.yaml`
- Create: `k8s/redis-service.yaml`
- Create: `k8s/celery-worker-deployment.yaml`
- Modify: `k8s/deployment.yaml`
- Modify: `README.md`

- [ ] **Step 1: Write the deployment manifests**

Create `k8s/redis-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
```

Create `k8s/redis-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
```

Create `k8s/celery-worker-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
        - name: celery-worker
          image: IMAGE_PLACEHOLDER
          command: ["celery", "-A", "src.async_jobs.celery_app.celery_app", "worker", "--loglevel=INFO"]
          env:
            - name: REDIS_URL
              value: redis://redis-service:6379/0
```

Update `k8s/deployment.yaml` with:

```yaml
- name: REDIS_URL
  value: redis://redis-service:6379/0
- name: ASYNC_COZE_ENABLED
  value: "true"
```

- [ ] **Step 2: Update README deployment notes**

Add Redis + Celery worker to the deployment overview and async architecture notes.

- [ ] **Step 3: Commit**

```bash
git add k8s/redis-deployment.yaml k8s/redis-service.yaml k8s/celery-worker-deployment.yaml k8s/deployment.yaml README.md
git commit -m "ops: add redis and celery worker deployment manifests"
```

### Task 8: Final Verification

**Files:**
- Test: `tests/unit/test_async_job_service.py`
- Test: `tests/unit/test_async_coze_execution_service.py`
- Test: `tests/integration/api/test_async_chat_api.py`

- [ ] **Step 1: Run the focused async unit and API tests**

Run: `pytest tests/unit/test_async_job_service.py tests/unit/test_async_coze_execution_service.py tests/integration/api/test_async_chat_api.py -v`

Expected: PASS

- [ ] **Step 2: Run a smoke-level app test**

Run: `pytest tests/integration/api/test_chat_api.py -k "chat" -v`

Expected: Existing non-Coze chat flows remain green.

- [ ] **Step 3: Manual verification**

Run locally or in a test environment:

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "{\"message\":\"ai daily news\",\"conversation_id\":\"async-smoke-1\"}"
```

Expected:
- HTTP `202`
- JSON with `job_id` and `status`

Then:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/jobs/<job_id>
```

Expected:
- `queued` or `running` first
- eventually `completed` with the final assistant response

- [ ] **Step 4: Commit final polish if needed**

```bash
git add .
git commit -m "test: verify async coze execution flow"
```
