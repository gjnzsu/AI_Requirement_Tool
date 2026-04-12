"""Runtime container for Flask web app dependencies and shared state."""

import concurrent.futures
import copy
import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class ChatExecutionResult:
    """Structured result for one request-scoped chatbot execution."""

    response: str
    conversation_id: str
    chatbot: Any
    usage_info: Optional[Dict[str, Any]] = None
    ui_actions: Optional[list[dict[str, str]]] = None
    workflow_progress: Optional[list[dict[str, Any]]] = None


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

    def ensure_conversation(
        self,
        *,
        conversation_id: Optional[str],
        title: str,
        generator: Callable[[], str],
        memory_manager: Optional[Any] = None,
    ) -> str:
        """Ensure a conversation exists in the active storage backend."""
        memory_manager = self.memory_manager if memory_manager is None else memory_manager

        if memory_manager:
            if conversation_id and memory_manager.get_conversation(conversation_id):
                return conversation_id

            conversation_id = conversation_id or generator()
            memory_manager.create_conversation(conversation_id, title=title)
            return conversation_id

        if conversation_id and conversation_id in self.conversations:
            return conversation_id

        conversation_id = conversation_id or generator()
        now = datetime.now().isoformat()
        self.conversations[conversation_id] = {
            "messages": [],
            "title": title,
            "created_at": now,
            "updated_at": now,
        }
        return conversation_id

    def execute_chat_request(
        self,
        *,
        message: str,
        conversation_id: str,
        model: str,
        agent_mode: Optional[str] = None,
        chatbot: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
    ) -> ChatExecutionResult:
        """Run one request-scoped chat execution and restore shared chatbot state afterwards."""
        chatbot = chatbot or self.get_chatbot()
        memory_manager = self.memory_manager if memory_manager is None else memory_manager

        with self.chatbot_request_lock:
            snapshot = self._snapshot_chatbot_state(chatbot)
            try:
                if chatbot.provider_name.lower() != model.lower():
                    chatbot.switch_provider(model)

                chatbot.set_conversation_id(conversation_id)

                if memory_manager:
                    chatbot.load_conversation(conversation_id)
                else:
                    self._load_in_memory_conversation(chatbot, conversation_id)

                if agent_mode and hasattr(chatbot, "set_selected_agent_mode"):
                    chatbot.set_selected_agent_mode(agent_mode)

                response = chatbot.get_response(message)
                usage_info = copy.deepcopy(getattr(chatbot, "last_usage", None))

                runtime_state = copy.deepcopy(
                    getattr(chatbot, "export_runtime_state", lambda: {})()
                )
                ui_actions = self._build_ui_actions(runtime_state)
                workflow_progress = copy.deepcopy(
                    getattr(
                        getattr(chatbot, "agent", None),
                        "export_latest_requirement_workflow_progress",
                        lambda: None,
                    )()
                )

                if not memory_manager:
                    self._sync_in_memory_conversation(conversation_id, chatbot)
                elif hasattr(memory_manager, "update_conversation_metadata"):
                    memory_manager.update_conversation_metadata(conversation_id, runtime_state)

                return ChatExecutionResult(
                    response=response,
                    conversation_id=conversation_id,
                    chatbot=chatbot,
                    usage_info=usage_info,
                    ui_actions=ui_actions,
                    workflow_progress=workflow_progress,
                )
            finally:
                self._restore_chatbot_state(chatbot, snapshot)

    def _build_ui_actions(
        self,
        runtime_state: Optional[Dict[str, Any]],
    ) -> Optional[list[dict[str, str]]]:
        """Return lightweight UI actions for the active conversation state."""
        requirement_state = (runtime_state or {}).get("requirement_sdlc_agent_state") or {}
        if requirement_state.get("stage") == "confirmation":
            return [
                {"label": "Approve", "value": "approve", "kind": "primary"},
                {"label": "Cancel", "value": "cancel", "kind": "secondary"},
            ]
        return None

    def _snapshot_chatbot_state(self, chatbot: Any) -> Dict[str, Any]:
        """Capture mutable chatbot request state so it can be restored after execution."""
        return {
            "conversation_id": getattr(chatbot, "conversation_id", None),
            "provider_name": getattr(chatbot, "provider_name", None),
            "provider_manager": getattr(chatbot, "provider_manager", None),
            "llm_provider": getattr(chatbot, "llm_provider", None),
            "agent_provider_name": getattr(getattr(chatbot, "agent", None), "provider_name", None),
            "agent_llm": getattr(getattr(chatbot, "agent", None), "llm", None),
            "conversation_history": copy.deepcopy(getattr(chatbot, "conversation_history", [])),
            "last_usage": copy.deepcopy(getattr(chatbot, "last_usage", None)),
            "workflow_progress": copy.deepcopy(
                getattr(
                    getattr(chatbot, "agent", None),
                    "export_latest_requirement_workflow_progress",
                    lambda: None,
                )()
            ),
            "runtime_state": copy.deepcopy(
                getattr(chatbot, "export_runtime_state", lambda: {})()
            ),
        }

    def _restore_chatbot_state(self, chatbot: Any, snapshot: Dict[str, Any]) -> None:
        """Restore mutable chatbot request state after one request finishes."""
        if hasattr(chatbot, "provider_name"):
            chatbot.provider_name = snapshot.get("provider_name")
        if hasattr(chatbot, "provider_manager"):
            chatbot.provider_manager = snapshot.get("provider_manager")
        if hasattr(chatbot, "llm_provider"):
            chatbot.llm_provider = snapshot.get("llm_provider")

        agent = getattr(chatbot, "agent", None)
        if agent is not None:
            if hasattr(agent, "provider_name"):
                agent.provider_name = snapshot.get("agent_provider_name")
            if hasattr(agent, "llm"):
                agent.llm = snapshot.get("agent_llm")

        if hasattr(chatbot, "conversation_id"):
            chatbot.conversation_id = snapshot.get("conversation_id")
        if hasattr(chatbot, "conversation_history"):
            chatbot.conversation_history = snapshot.get("conversation_history", [])
        if hasattr(chatbot, "last_usage"):
            chatbot.last_usage = snapshot.get("last_usage")
        agent = getattr(chatbot, "agent", None)
        if agent is not None and hasattr(agent, "load_latest_requirement_workflow_progress"):
            agent.load_latest_requirement_workflow_progress(
                copy.deepcopy(snapshot.get("workflow_progress"))
            )
        if hasattr(chatbot, "load_runtime_state"):
            chatbot.load_runtime_state(copy.deepcopy(snapshot.get("runtime_state", {})))

    def _load_in_memory_conversation(self, chatbot: Any, conversation_id: str) -> None:
        """Load request-scoped in-memory history into the shared chatbot instance."""
        conversation = self.conversations.get(conversation_id, {})
        chatbot.conversation_history = copy.deepcopy(conversation.get("messages", []))
        if hasattr(chatbot, "load_runtime_state"):
            chatbot.load_runtime_state(copy.deepcopy(conversation.get("metadata", {})))

    def _sync_in_memory_conversation(self, conversation_id: str, chatbot: Any) -> None:
        """Persist updated in-memory history back into the runtime store."""
        now = datetime.now().isoformat()
        conversation = self.conversations.setdefault(
            conversation_id,
            {
                "messages": [],
                "title": "New Chat",
                "created_at": now,
                "updated_at": now,
            },
        )
        conversation["messages"] = copy.deepcopy(getattr(chatbot, "conversation_history", []))
        conversation["metadata"] = copy.deepcopy(
            getattr(chatbot, "export_runtime_state", lambda: {})()
        )
        conversation["updated_at"] = now



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
