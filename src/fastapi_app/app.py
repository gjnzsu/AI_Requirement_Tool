"""FastAPI application skeleton for the web runtime."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.config import Config
from src.fastapi_app.routes.auth import router as auth_router
from src.webapp import create_app_runtime, safe_print

try:
    from src.chatbot import Chatbot
except ImportError as error:
    safe_print(f"[WARNING] Could not import Chatbot: {error}")
    Chatbot = None

try:
    from src.services.memory_manager import MemoryManager
except ImportError as error:
    safe_print(f"[WARNING] Could not import MemoryManager: {error}")
    MemoryManager = None

try:
    from src.auth import AuthService, UserService
except ImportError as error:
    safe_print(f"[WARNING] Could not import auth modules: {error}")
    safe_print("  Authentication features will be disabled.")
    AuthService = None
    UserService = None


def create_fastapi_app() -> FastAPI:
    """Create the FastAPI application and initialize shared runtime once."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = create_app_runtime(
            config=Config,
            chatbot_class=Chatbot,
            memory_manager_class=MemoryManager,
            auth_service_class=AuthService,
            user_service_class=UserService,
            printer=safe_print,
        )
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
    app.include_router(auth_router)

    @app.get("/api/health")
    async def health():
        """Health check endpoint for probes and uptime checks."""
        return {"status": "ok"}

    return app