"""System tests for the FastAPI application skeleton."""

from fastapi.testclient import TestClient
from starlette.requests import Request

from src.fastapi_app.app import create_fastapi_app
from src.fastapi_app.dependencies import get_runtime


def test_fastapi_health_endpoint_returns_ok():
    """GET /api/health should return the shared health payload."""
    app = create_fastapi_app()

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_app_boot_initializes_runtime_once(monkeypatch):
    """The app should create the shared runtime once at startup, not per request."""
    created_runtimes = []

    class DummyRuntime:
        pass

    def fake_create_app_runtime(*args, **kwargs):
        runtime = DummyRuntime()
        created_runtimes.append(runtime)
        return runtime

    monkeypatch.setattr("src.fastapi_app.app.create_app_runtime", fake_create_app_runtime)

    app = create_fastapi_app()

    with TestClient(app) as client:
        first_response = client.get("/api/health")
        second_response = client.get("/api/health")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == {"status": "ok"}
    assert second_response.json() == {"status": "ok"}
    assert len(created_runtimes) == 1
    assert app.state.runtime is created_runtimes[0]


def test_get_runtime_returns_app_state_runtime():
    """The runtime dependency should return the app-state runtime object."""
    app = create_fastapi_app()
    runtime = object()
    app.state.runtime = runtime
    request = Request({"type": "http", "app": app})

    assert get_runtime(request) is runtime
