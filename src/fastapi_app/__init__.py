"""FastAPI application skeleton for the web runtime."""

from .app import create_fastapi_app
from .dependencies import get_runtime

__all__ = ["create_fastapi_app", "get_runtime"]
