"""FastAPI dependencies for accessing shared runtime state."""

from fastapi import Request

from src.webapp.runtime import AppRuntime


def get_runtime(request: Request) -> AppRuntime:
    """Return the shared AppRuntime stored on the FastAPI application state."""
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise RuntimeError("FastAPI runtime is not initialized.")
    return runtime
