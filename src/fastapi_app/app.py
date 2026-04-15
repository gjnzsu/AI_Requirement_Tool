"""FastAPI application factory for the web runtime scaffold."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.config import Config
from src.webapp import create_app_runtime, safe_print

from .dependencies import get_runtime


def create_fastapi_app() -> FastAPI:
    """Create the FastAPI application and initialize shared runtime once."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = create_app_runtime(config=Config, printer=safe_print)
        app.state.runtime = runtime
        yield

    app = FastAPI(
        title="AI Requirement Tool",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health():
        """Health check endpoint for probes and uptime checks."""
        return {"status": "ok"}

    @app.get("/api/runtime")
    async def runtime_info(runtime=Depends(get_runtime)):
        """Simple runtime-backed endpoint for future expansion."""
        return {"runtime_initialized": runtime is not None}

    return app
