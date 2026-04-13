"""FastAPI authentication routes with Flask contract parity."""

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from src.fastapi_app.dependencies import get_runtime
from src.fastapi_app.models import LoginResponse, LogoutResponse, MeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _error_response(status_code: int, error: str, message: str | None = None):
    payload = {"error": error}
    if message is not None:
        payload["message"] = message
    return JSONResponse(status_code=status_code, content=payload)


def _configured_error():
    return _error_response(
        503,
        "Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.",
    )


def _authenticate_request(runtime, authorization: str | None, *, missing_user_status: int, missing_user_error: str):
    auth_service = runtime.auth_service
    user_service = runtime.user_service

    if not auth_service or not user_service:
        return _configured_error()

    token = auth_service.extract_token_from_header(authorization)
    if not token:
        return _error_response(401, "Authentication required. Please provide a valid token.")

    payload = auth_service.verify_token(token)
    if not payload:
        return _error_response(401, "Invalid or expired token. Please login again.")

    user = user_service.get_user_by_id(payload.get("user_id"))
    if not user:
        return _error_response(missing_user_status, missing_user_error)

    return user


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, runtime=Depends(get_runtime)):
    """Authenticate a user and return a JWT token."""
    if not runtime.auth_service or not runtime.user_service:
        return _configured_error()

    try:
        data = await request.json()
        username = str((data or {}).get("username", "")).strip()
        password = str((data or {}).get("password", ""))

        if not username or not password:
            return _error_response(400, "Username and password are required")

        user = runtime.user_service.authenticate_user(username, password)
        if not user:
            return _error_response(401, "Invalid username or password")

        token = runtime.auth_service.generate_token(user["id"], user["username"])
        return {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
            },
        }
    except Exception as error:
        return _error_response(500, str(error))


@router.post("/logout", response_model=LogoutResponse)
async def logout(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    """Logout the current user."""
    result = _authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(result, JSONResponse):
        return result

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse)
async def get_current_user_info(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    """Return details for the currently authenticated user."""
    result = _authenticate_request(
        runtime,
        authorization,
        missing_user_status=404,
        missing_user_error="User not found",
    )
    if isinstance(result, JSONResponse):
        return result

    return {"user": result}