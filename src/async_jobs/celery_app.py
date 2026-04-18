"""Celery application configuration for async jobs."""

from __future__ import annotations

from functools import wraps
from types import SimpleNamespace

try:
    from celery import Celery
except ModuleNotFoundError:  # pragma: no cover - exercised when Celery is unavailable
    class _FallbackTask:
        """Callable task wrapper used when Celery is not installed."""

        def __init__(self, func, *, name: str) -> None:
            self.__wrapped__ = func
            self.name = name

        def __call__(self, *args, **kwargs):
            return self.__wrapped__(*args, **kwargs)

        def apply_async(self, *, kwargs):
            return SimpleNamespace(id="local-job-id", kwargs=kwargs)

    class Celery:  # type: ignore[no-redef]
        """Lightweight fallback used when Celery is not installed."""

        def __init__(self, name: str) -> None:
            self.main = name
            self.conf = {}
            self._tasks: dict[str, object] = {}

        def task(self, name: str | None = None):
            def decorator(func):
                task_name = name or func.__name__

                @wraps(func)
                def wrapped(*args, **kwargs):
                    return func(*args, **kwargs)

                task = _FallbackTask(wrapped, name=task_name)
                self._tasks[task_name] = task
                return task

            return decorator

        def AsyncResult(self, job_id: str):  # noqa: N802
            return SimpleNamespace(id=job_id, state="PENDING", result=None)

from config.config import Config


celery_app = Celery("src.async_jobs")
celery_app.conf.update(
    broker_url=Config.CELERY_BROKER_URL,
    result_backend=Config.CELERY_RESULT_BACKEND,
    result_expires=Config.CELERY_RESULT_TTL_SECONDS,
    task_time_limit=Config.CELERY_TASK_TIME_LIMIT,
    task_track_started=True,
)


from src.async_jobs.tasks import process_coze_job  # noqa: E402  # isort: skip
