"""Runtime container for Flask web app dependencies and shared state."""

import concurrent.futures
import os
import sys
import threading
from typing import Any, Callable, Dict, Optional

from flask import current_app, has_app_context
from werkzeug.local import LocalProxy


def safe_print(message: str) -> None:
    """Print safely on Windows terminals that may not support Unicode."""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.encode("ascii", "replace").decode("ascii")
        print(safe_message)


class AppRuntime:
    """Owns shared application services that were previously module globals."""

    def __init__(
        self,
        config: Any,
        chatbot_class: Optional[type] = None,
        memory_manager_class: Optional[type] = None,
        auth_service_class: Optional[type] = None,
        user_service_class: Optional[type] = None,
        printer: Callable[[str], None] = safe_print,
    ) -> None:
        self.config = config
        self.chatbot_class = chatbot_class
        self.memory_manager_class = memory_manager_class
        self.auth_service_class = auth_service_class
        self.user_service_class = user_service_class
        self.printer = printer
        self.chatbot_instance: Optional[Any] = None
        self.memory_manager: Optional[Any] = None
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.auth_service: Optional[Any] = None
        self.user_service: Optional[Any] = None
        self._chatbot_lock = threading.Lock()
        self.chatbot_request_lock = threading.Lock()

    def initialize(self) -> "AppRuntime":
        """Initialize eagerly loaded services needed by HTTP handlers."""
        self._initialize_auth_services()
        self._initialize_memory_manager()
        return self

    def _initialize_auth_services(self) -> None:
        if self.auth_service_class is None or self.user_service_class is None:
            self.printer("[WARNING] Authentication modules not available. Authentication will be disabled.")
            return

        try:
            self.auth_service = self.auth_service_class()
            db_path = self.config.AUTH_DB_PATH
            self.printer("[OK] Initialized Authentication services")
            self.printer(f"     Config.AUTH_DB_PATH: {db_path}")
            self.printer(f"     Environment AUTH_DB_PATH: {os.getenv('AUTH_DB_PATH', 'Not set')}")
            self.user_service = self.user_service_class(db_path=db_path)
            actual_db_path = self.user_service.db_path
            self.printer(f"     Using database at: {actual_db_path}")
            try:
                users = self.user_service.list_users()
                self.printer(f"     Users in database: {len(users)}")
                for user in users:
                    self.printer(f"       - ID: {user['id']}, Username: {user['username']}")
            except Exception as error:
                self.printer(f"     Warning: Could not list users: {error}")
        except ValueError as error:
            self.printer(f"[WARNING] Authentication initialization warning: {error}")
            self.printer("   Authentication will be disabled. Set JWT_SECRET_KEY in .env to enable.")
            self.auth_service = None
            self.user_service = None
        except Exception as error:
            self.printer(f"[WARNING] Failed to initialize Authentication services: {error}")
            self.printer("   Authentication will be disabled.")
            self.auth_service = None
            self.user_service = None

    def _initialize_memory_manager(self) -> None:
        if self.memory_manager_class is None:
            self.printer("[WARNING] MemoryManager not available. Using in-memory storage.")
            return

        if not self.config.USE_PERSISTENT_MEMORY:
            self.printer("[WARNING] Persistent memory disabled (USE_PERSISTENT_MEMORY=false)")
            return

        try:
            self.memory_manager = self.memory_manager_class(
                db_path=self.config.MEMORY_DB_PATH,
                max_context_messages=self.config.MAX_CONTEXT_MESSAGES,
            )
            self.printer("[OK] Initialized Memory Manager for web app")
        except Exception as error:
            self.printer(f"[WARNING] Failed to initialize Memory Manager: {error}")
            self.printer("   Falling back to in-memory storage")
            self.memory_manager = None

    def _create_chatbot(self) -> Any:
        return self.chatbot_class(
            provider_name=None,
            use_fallback=True,
            temperature=0.7,
            max_history=self.config.MAX_CONTEXT_MESSAGES // 2,
            use_persistent_memory=self.config.USE_PERSISTENT_MEMORY,
            memory_db_path=self.config.MEMORY_DB_PATH,
            use_rag=getattr(self.config, "USE_RAG", True),
            rag_top_k=getattr(self.config, "RAG_TOP_K", 3),
            enable_mcp_tools=getattr(self.config, "ENABLE_MCP_TOOLS", True),
            lazy_load_tools=True,
            use_agent=True,
            use_mcp=self.config.USE_MCP,
            config=self.config,
        )

    def get_chatbot(self) -> Any:
        """Create the chatbot lazily and reuse it across requests."""
        if self.chatbot_class is None:
            raise RuntimeError("Chatbot module is not available. Please install required dependencies.")

        if self.chatbot_instance is not None:
            return self.chatbot_instance

        with self._chatbot_lock:
            if self.chatbot_instance is not None:
                return self.chatbot_instance

            self.printer("=" * 70)
            self.printer("[INFO] Creating Chatbot Instance")
            self.printer("=" * 70)
            self.printer(f"   Provider: {self.config.LLM_PROVIDER}")
            self.printer(f"   Model: {self.config.get_llm_model()}")
            self.printer(f"   MCP Enabled: {self.config.USE_MCP}")
            self.printer(f"   RAG Enabled: {getattr(self.config, 'USE_RAG', True)}")
            self.printer(f"   Tools Enabled: {getattr(self.config, 'ENABLE_MCP_TOOLS', True)}")
            self.printer("=" * 70)

            try:
                if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("TESTING"):
                    self.chatbot_instance = self._create_chatbot()
                else:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._create_chatbot)
                        try:
                            self.chatbot_instance = future.result(timeout=120.0)
                        except concurrent.futures.TimeoutError as error:
                            raise RuntimeError(
                                "Chatbot initialization timed out after 120 seconds. "
                                "This may indicate a configuration issue or network problem."
                            ) from error
            except Exception as error:
                self.printer(f"[ERROR] Chatbot initialization failed: {error}")
                raise

            self.printer("=" * 70)
            self.printer("[OK] Chatbot Instance Created Successfully")
            self.printer("=" * 70)
            return self.chatbot_instance


def create_app_runtime(
    config: Any,
    chatbot_class: Optional[type] = None,
    memory_manager_class: Optional[type] = None,
    auth_service_class: Optional[type] = None,
    user_service_class: Optional[type] = None,
    printer: Callable[[str], None] = safe_print,
) -> AppRuntime:
    """Create and initialize the shared runtime used by Flask handlers."""
    return AppRuntime(
        config=config,
        chatbot_class=chatbot_class,
        memory_manager_class=memory_manager_class,
        auth_service_class=auth_service_class,
        user_service_class=user_service_class,
        printer=printer,
    ).initialize()


def get_app_runtime(fallback: Optional[AppRuntime] = None) -> AppRuntime:
    """Return the active runtime from Flask, or a provided fallback outside app context."""
    if has_app_context():
        runtime = current_app.extensions.get("chatbot_runtime")
        if runtime is not None:
            _sync_runtime_from_app_module(runtime)
            return runtime

    if fallback is not None:
        return fallback

    raise RuntimeError("Chatbot runtime is not initialized.")


def _sync_runtime_from_app_module(runtime: AppRuntime) -> None:
    """Preserve compatibility with tests that monkeypatch app module globals."""
    app_module = sys.modules.get("app")
    if app_module is None:
        return

    for attribute_name in (
        "auth_service",
        "user_service",
        "memory_manager",
        "chatbot_instance",
        "conversations",
    ):
        if attribute_name not in app_module.__dict__:
            continue

        module_value = app_module.__dict__[attribute_name]
        if not isinstance(module_value, LocalProxy):
            setattr(runtime, attribute_name, module_value)
