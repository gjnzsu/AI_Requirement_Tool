"""Error-contract tests for FastAPI API endpoints."""

from types import SimpleNamespace

from fastapi import Request
from fastapi.testclient import TestClient

from src.fastapi_app.app import create_fastapi_app


def _build_client(monkeypatch):
    runtime = SimpleNamespace(
        auth_service=None,
        user_service=None,
        memory_manager=None,
        conversations={},
    )

    def fake_create_app_runtime(*args, **kwargs):
        return runtime

    monkeypatch.setattr("src.fastapi_app.app.create_app_runtime", fake_create_app_runtime)
    app = create_fastapi_app()
    return app, TestClient(app, raise_server_exceptions=False)


def test_api_not_found_returns_flask_style_json(monkeypatch):
    app, client = _build_client(monkeypatch)

    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": "Not Found", "message": "Not Found"}


def test_api_method_not_allowed_returns_flask_style_json(monkeypatch):
    app, client = _build_client(monkeypatch)

    response = client.post("/api/health")

    assert response.status_code == 405
    assert response.json() == {
        "error": "Method Not Allowed",
        "message": "Method Not Allowed",
    }


def test_unhandled_api_exception_returns_internal_server_json(monkeypatch):
    app, client = _build_client(monkeypatch)

    @app.get("/api/test-error")
    async def crash(_request: Request):
        raise RuntimeError("boom")

    response = client.get("/api/test-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": "Internal Server Error",
        "message": "boom",
    }
