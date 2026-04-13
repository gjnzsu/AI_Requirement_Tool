"""FastAPI system routes and API error-contract handlers."""

from http import HTTPStatus

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

router = APIRouter(tags=["system"])


@router.get("/api/health")
async def health():
    """Health check endpoint for probes and uptime checks."""
    return {"status": "ok"}


if PROMETHEUS_AVAILABLE:
    @router.get("/metrics")
    async def metrics():
        """Expose Prometheus metrics when prometheus_client is installed."""
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def register_error_handlers(app: FastAPI) -> None:
    """Register Flask-style JSON error payloads for API endpoints."""

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/api/"):
            status_name = HTTPStatus(exc.status_code).phrase
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": status_name, "message": str(exc.detail)},
            )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=400,
                content={"error": "Bad Request", "message": "Invalid request parameters."},
            )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error", "message": str(exc)},
            )
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
