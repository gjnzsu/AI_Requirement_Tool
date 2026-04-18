"""Tests for GET /api/jobs/<job_id> endpoint."""

import pytest
from unittest.mock import Mock, patch


def build_runtime_with_job_service(job_service):
    runtime = Mock()
    runtime._get_async_job_service = Mock(return_value=job_service)
    return runtime


@pytest.mark.integration
@pytest.mark.api
class TestJobsAPI:
    def test_get_job_returns_queued_status(self, test_client):
        job_service = Mock()
        job_service.get_job_status.return_value = {"job_id": "job-123", "status": "queued"}
        runtime = build_runtime_with_job_service(job_service)

        with patch("src.webapp.routes.jobs.get_app_runtime", return_value=runtime):
            response = test_client.get("/api/jobs/job-123")

        assert response.status_code == 200
        assert response.get_json() == {"job_id": "job-123", "status": "queued"}

    @pytest.mark.parametrize(
        "payload",
        [
            {"job_id": "job-123", "status": "running"},
            {"job_id": "job-123", "status": "completed", "result": {"answer": "done"}},
            {"job_id": "job-123", "status": "failed", "error": "boom"},
        ],
    )
    def test_get_job_returns_terminal_and_running_statuses(self, test_client, payload):
        job_service = Mock()
        job_service.get_job_status.return_value = payload
        runtime = build_runtime_with_job_service(job_service)

        with patch("src.webapp.routes.jobs.get_app_runtime", return_value=runtime):
            response = test_client.get("/api/jobs/job-123")

        assert response.status_code == 200
        assert response.get_json() == payload

    def test_get_job_returns_404_for_missing_job(self, test_client):
        from src.services.async_job_service import AsyncJobNotFoundError

        job_service = Mock()
        job_service.get_job_status.side_effect = AsyncJobNotFoundError("job-404")
        runtime = build_runtime_with_job_service(job_service)

        with patch("src.webapp.routes.jobs.get_app_runtime", return_value=runtime):
            response = test_client.get("/api/jobs/job-404")

        assert response.status_code == 404
        assert response.get_json() == {"error": "Job not found", "job_id": "job-404"}
