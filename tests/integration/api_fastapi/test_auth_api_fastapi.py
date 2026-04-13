"""Parity tests for the FastAPI authentication API."""

from datetime import datetime, timedelta
import os
import secrets
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.config import Config
from src.auth.auth_service import AuthService
from src.auth.user_service import UserService
from src.fastapi_app.app import create_fastapi_app


@pytest.fixture(scope="function")
def temp_auth_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield db_path
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture(scope="function")
def auth_setup(temp_auth_db, monkeypatch):
    test_secret = secrets.token_urlsafe(32)
    monkeypatch.setattr(Config, "JWT_SECRET_KEY", test_secret)
    monkeypatch.setattr(Config, "JWT_EXPIRATION_HOURS", 24)
    monkeypatch.setattr(Config, "AUTH_DB_PATH", temp_auth_db)

    auth_service = AuthService()
    user_service = UserService(db_path=temp_auth_db)
    test_user = user_service.create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123",
    )

    return auth_service, user_service, test_user, test_secret


@pytest.fixture(scope="function")
def fastapi_client(monkeypatch, auth_setup):
    auth_service, user_service, test_user, _ = auth_setup
    runtime = SimpleNamespace(auth_service=auth_service, user_service=user_service)

    def fake_create_app_runtime(*args, **kwargs):
        return runtime

    monkeypatch.setattr("src.fastapi_app.app.create_app_runtime", fake_create_app_runtime)

    app = create_fastapi_app()
    with TestClient(app) as client:
        yield client, runtime, test_user


def test_login_success_returns_token_and_user(fastapi_client):
    client, runtime, test_user = fastapi_client

    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"token", "user"}
    assert data["user"]["id"] == test_user["id"]
    assert data["user"]["username"] == "testuser"
    assert data["user"]["email"] == "test@example.com"
    assert set(data["user"].keys()) == {"id", "username", "email"}
    payload = runtime.auth_service.verify_token(data["token"])
    assert payload is not None
    assert payload["user_id"] == test_user["id"]
    assert payload["username"] == "testuser"


def test_login_failure_returns_401_and_error_key(fastapi_client):
    client, _, _ = fastapi_client

    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    data = response.json()
    assert set(data.keys()) == {"error"}
    assert "invalid" in data["error"].lower()


def test_logout_requires_token(fastapi_client):
    client, _, _ = fastapi_client

    response = client.post("/api/auth/logout")

    assert response.status_code == 401
    assert response.json() == {"error": "Authentication required. Please provide a valid token."}


def test_me_returns_current_user_for_valid_token(fastapi_client):
    client, runtime, test_user = fastapi_client
    token = runtime.auth_service.generate_token(test_user["id"], test_user["username"])

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"user": test_user}


def test_me_returns_404_when_current_user_missing(fastapi_client):
    client, runtime, test_user = fastapi_client
    token = runtime.auth_service.generate_token(test_user["id"], test_user["username"])
    runtime.user_service.get_user_by_id = lambda user_id: None

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"error": "User not found"}


def test_auth_errors_match_flask_payload_shape(fastapi_client):
    client, runtime, test_user = fastapi_client
    invalid_token = jwt.encode(
        {
            "user_id": test_user["id"],
            "username": test_user["username"],
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
        },
        runtime.auth_service.secret_key,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "message" not in data


def test_auth_bypass_matches_flask_behavior(fastapi_client, monkeypatch):
    client, _, _ = fastapi_client
    monkeypatch.setenv("BYPASS_AUTH", "1")

    me_response = client.get("/api/auth/me")
    logout_response = client.post("/api/auth/logout")

    assert me_response.status_code == 200
    assert me_response.json() == {
        "user": {"id": 1, "username": "test_user", "email": "test@example.com"}
    }
    assert logout_response.status_code == 200
    assert logout_response.json() == {"success": True, "message": "Logged out successfully"}


def test_me_returns_structured_json_error_on_auth_dependency_failure(fastapi_client):
    client, runtime, test_user = fastapi_client
    token = runtime.auth_service.generate_token(test_user["id"], test_user["username"])

    def explode(_):
        raise RuntimeError("db temporarily unavailable")

    runtime.user_service.get_user_by_id = explode

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "Authentication error",
        "message": "db temporarily unavailable",
    }
