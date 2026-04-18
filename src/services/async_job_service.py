"""Application service for async job handling."""

from __future__ import annotations

from typing import Any, Dict

from config.config import Config
from src.async_jobs.celery_app import celery_app, process_coze_job

_DEFAULT_KNOWN_JOB_STORE = object()


class AsyncJobNotFoundError(LookupError):
    """Raised when a polled async job is unknown or has expired."""

    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)
        self.job_id = job_id


class AsyncJobService:
    """Enqueue and inspect async jobs."""

    def __init__(
        self,
        *,
        celery_app=celery_app,
        coze_job_task=process_coze_job,
        known_job_store: Any = _DEFAULT_KNOWN_JOB_STORE,
        known_job_ttl_seconds: int = Config.CELERY_RESULT_TTL_SECONDS,
        known_job_prefix: str = "async-job:",
    ) -> None:
        self.celery_app = celery_app
        self.coze_job_task = coze_job_task
        self.known_job_store = (
            self._build_known_job_store(celery_app)
            if known_job_store is _DEFAULT_KNOWN_JOB_STORE
            else known_job_store
        )
        self.known_job_ttl_seconds = known_job_ttl_seconds
        self.known_job_prefix = known_job_prefix

    def enqueue_coze_job(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Enqueue a Coze job payload."""
        async_result = self.coze_job_task.apply_async(kwargs=payload)
        self._mark_known_job(async_result.id)
        return {"job_id": async_result.id, "status": "queued"}

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Return a normalized job status payload."""
        async_result = self.celery_app.AsyncResult(job_id)
        if async_result.state == "PENDING" and not self._is_known_job(job_id):
            raise AsyncJobNotFoundError(job_id)

        status_map = {
            "PENDING": "queued",
            "STARTED": "running",
            "SUCCESS": "completed",
            "FAILURE": "failed",
        }
        status = status_map.get(async_result.state, async_result.state.lower())
        payload: Dict[str, Any] = {"job_id": job_id, "status": status}

        if async_result.state == "SUCCESS":
            payload["result"] = async_result.result
        elif async_result.state == "FAILURE":
            payload["error"] = str(async_result.result)

        return payload

    def _job_key(self, job_id: str) -> str:
        return f"{self.known_job_prefix}{job_id}"

    def _mark_known_job(self, job_id: str) -> None:
        if self.known_job_store is None:
            return

        job_key = self._job_key(job_id)
        if hasattr(self.known_job_store, "setex"):
            self.known_job_store.setex(job_key, self.known_job_ttl_seconds, "1")
            return

        set_method = getattr(self.known_job_store, "set", None)
        if callable(set_method):
            set_method(job_key, "1", ex=self.known_job_ttl_seconds)

    def _is_known_job(self, job_id: str) -> bool:
        if self.known_job_store is None:
            return False

        job_key = self._job_key(job_id)
        exists_method = getattr(self.known_job_store, "exists", None)
        if callable(exists_method):
            return bool(exists_method(job_key))

        get_method = getattr(self.known_job_store, "get", None)
        if callable(get_method):
            return get_method(job_key) is not None

        return False

    @staticmethod
    def _build_known_job_store(celery_app_instance: Any) -> Any:
        backend = getattr(celery_app_instance, "backend", None)
        backend_client = getattr(backend, "client", None)
        if backend_client is not None and hasattr(backend_client, "setex"):
            return backend_client

        try:
            import redis

            return redis.Redis.from_url(Config.REDIS_URL)
        except Exception:
            return None
