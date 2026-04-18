"""Unit tests for async job service."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.services.async_job_service import AsyncJobService, AsyncJobNotFoundError


@dataclass
class _FakeAsyncResult:
    state: str
    result: object = None


class _FakeTask:
    def __init__(self) -> None:
        self.kwargs = None

    def apply_async(self, *, kwargs):
        self.kwargs = kwargs
        return type("_FakeTaskResult", (), {"id": "job-123"})()


class _FakeCeleryApp:
    def __init__(self, async_result: _FakeAsyncResult) -> None:
        self.async_result = async_result
        self.requested_job_id = None

    def AsyncResult(self, job_id: str) -> _FakeAsyncResult:  # noqa: N802
        self.requested_job_id = job_id
        return self.async_result


class _FakeKnownJobStore:
    def __init__(self, known_job_ids=None) -> None:
        self.known_job_ids = set(known_job_ids or [])
        self.setex_calls = []

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.setex_calls.append((key, ttl_seconds, value))
        self.known_job_ids.add(key)

    def exists(self, key: str) -> bool:
        return key in self.known_job_ids

    def expire_key(self, key: str) -> None:
        self.known_job_ids.discard(key)


@pytest.mark.unit
def test_enqueue_coze_job_returns_queued_job_id():
    task = _FakeTask()
    known_job_store = _FakeKnownJobStore()
    service = AsyncJobService(
        celery_app=object(),
        coze_job_task=task,
        known_job_store=known_job_store,
        known_job_ttl_seconds=123,
    )

    result = service.enqueue_coze_job({"prompt": "hello"})

    assert result == {"job_id": "job-123", "status": "queued"}
    assert task.kwargs == {"prompt": "hello"}
    assert known_job_store.setex_calls == [("async-job:job-123", 123, "1")]


@pytest.mark.unit
def test_get_job_status_maps_success_to_completed():
    service = AsyncJobService(
        celery_app=_FakeCeleryApp(_FakeAsyncResult(state="SUCCESS", result={"ok": True})),
        coze_job_task=object(),
        known_job_store=_FakeKnownJobStore({"async-job:job-123"}),
    )

    result = service.get_job_status("job-123")

    assert result == {
        "job_id": "job-123",
        "status": "completed",
        "result": {"ok": True},
    }
    assert service.celery_app.requested_job_id == "job-123"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("state", "expected_status"),
    [
        ("PENDING", "queued"),
        ("STARTED", "running"),
    ],
)
def test_get_job_status_maps_pending_and_started_states(state: str, expected_status: str):
    service = AsyncJobService(
        celery_app=_FakeCeleryApp(_FakeAsyncResult(state=state)),
        coze_job_task=object(),
        known_job_store=_FakeKnownJobStore({"async-job:job-123"}),
    )

    result = service.get_job_status("job-123")

    assert result == {"job_id": "job-123", "status": expected_status}
    assert service.celery_app.requested_job_id == "job-123"


@pytest.mark.unit
def test_get_job_status_maps_failure_to_failed_with_error():
    service = AsyncJobService(
        celery_app=_FakeCeleryApp(_FakeAsyncResult(state="FAILURE", result=RuntimeError("boom"))),
        coze_job_task=object(),
        known_job_store=_FakeKnownJobStore({"async-job:job-123"}),
    )

    result = service.get_job_status("job-123")

    assert result == {
        "job_id": "job-123",
        "status": "failed",
        "error": "boom",
    }
    assert service.celery_app.requested_job_id == "job-123"


@pytest.mark.unit
def test_get_job_status_raises_not_found_for_unknown_pending_job():
    service = AsyncJobService(
        celery_app=_FakeCeleryApp(_FakeAsyncResult(state="PENDING")),
        coze_job_task=object(),
        known_job_store=_FakeKnownJobStore(),
    )

    with pytest.raises(AsyncJobNotFoundError):
        service.get_job_status("job-missing")


@pytest.mark.unit
def test_get_job_status_raises_not_found_for_pending_job_when_marker_tracking_unavailable():
    service = AsyncJobService(
        celery_app=_FakeCeleryApp(_FakeAsyncResult(state="PENDING")),
        coze_job_task=object(),
        known_job_store=None,
    )

    with pytest.raises(AsyncJobNotFoundError):
        service.get_job_status("job-missing")


@pytest.mark.unit
def test_get_job_status_raises_not_found_after_known_job_marker_expires():
    known_job_store = _FakeKnownJobStore()
    task = _FakeTask()
    service = AsyncJobService(
        celery_app=_FakeCeleryApp(_FakeAsyncResult(state="PENDING")),
        coze_job_task=task,
        known_job_store=known_job_store,
    )

    enqueue_result = service.enqueue_coze_job({"prompt": "hello"})
    known_job_store.expire_key("async-job:job-123")

    with pytest.raises(AsyncJobNotFoundError):
        service.get_job_status(enqueue_result["job_id"])
