"""FastAPI authentication routes with Flask contract parity."""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from src.fastapi_app.dependencies import authenticate_request, configured_error, error_response, get_runtime
from src.fastapi_app.models import LoginRequest, LoginResponse, LogoutResponse, MeResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, runtime=Depends(get_runtime)):
    """Authenticate a user and return a JWT token."""
    if not runtime.auth_service or not runtime.user_service:
        return configured_error()

    try:
        username = payload.username.strip()
        password = payload.password

        if not username or not password:
            return error_response(400, "Username and password are required")

        user = runtime.user_service.authenticate_user(username, password)
        if not user:
            return error_response(401, "Invalid username or password")

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
        return error_response(500, str(error))


@router.post("/logout", response_model=LogoutResponse)
async def logout(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    """Logout the current user."""
    result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=401,
        missing_user_error="User not found or inactive.",
    )
    if isinstance(result, JSONResponse):
        return result

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me", response_model=MeResponse, response_model_exclude_none=True)
async def get_current_user_info(authorization: str | None = Header(default=None), runtime=Depends(get_runtime)):
    """Return details for the currently authenticated user."""
    result = authenticate_request(
        runtime,
        authorization,
        missing_user_status=404,
        missing_user_error="User not found",
    )
    if isinstance(result, JSONResponse):
        return result

    return {"user": result}
