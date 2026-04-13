"""FastAPI dependencies for accessing shared runtime state."""

import os

from fastapi import Request
from fastapi.responses import JSONResponse

from src.webapp.runtime import AppRuntime


def get_runtime(request: Request) -> AppRuntime:
    """Return the shared AppRuntime stored on the FastAPI application state."""
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise RuntimeError("FastAPI runtime is not initialized.")
    return runtime


def error_response(status_code: int, error: str, message: str | None = None) -> JSONResponse:
    """Build a JSON error payload matching Flask API contract shape."""
    payload = {"error": error}
    if message is not None:
        payload["message"] = message
    return JSONResponse(status_code=status_code, content=payload)


def configured_error() -> JSONResponse:
    """Shared auth-not-configured response payload."""
    return error_response(
        503,
        "Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.",
    )


def is_bypass_auth_enabled() -> bool:
    """Mirror Flask BYPASS_AUTH behavior used by non-auth integration tests."""
    return os.environ.get("BYPASS_AUTH", "").strip() in {"1", "true", "True", "yes", "YES"}


def authenticate_request(
    runtime: AppRuntime,
    authorization: str | None,
    *,
    missing_user_status: int,
    missing_user_error: str,
) -> dict | JSONResponse:
    """Return authenticated user dict, or JSONResponse on auth/config failure."""
    auth_service = runtime.auth_service
    user_service = runtime.user_service

    if is_bypass_auth_enabled():
        return {"id": 1, "username": "test_user", "email": "test@example.com"}

    if not auth_service or not user_service:
        return configured_error()

    try:
        token = auth_service.extract_token_from_header(authorization)
        if not token:
            return error_response(401, "Authentication required. Please provide a valid token.")

        payload = auth_service.verify_token(token)
        if not payload:
            return error_response(401, "Invalid or expired token. Please login again.")

        user = user_service.get_user_by_id(payload.get("user_id"))
        if not user:
            return error_response(missing_user_status, missing_user_error)
    except Exception as error:
        return error_response(500, "Authentication error", str(error))

    return user
