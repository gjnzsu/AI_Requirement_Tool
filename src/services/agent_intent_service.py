"""Intent detection and routing policy for the chatbot agent."""

from __future__ import annotations

import concurrent.futures
from typing import Any, Callable, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage

from src.utils.logger import get_logger


logger = get_logger("chatbot.intent_service")


class AgentIntentService:
    """Encapsulate intent detection and post-detection routing policy."""

    def __init__(
        self,
        *,
        config: Any,
        detect_keyword_intent_fn: Callable[..., Optional[str]],
        rag_service_available: bool,
        jira_available: bool,
        coze_client: Any,
        use_mcp: bool,
        mcp_integration: Any,
        jira_tool: Any,
        get_cached_intent: Callable[[str], Optional[Dict[str, Any]]],
        cache_intent: Callable[[str, Dict[str, Any]], None],
        initialize_intent_detector: Callable[[], Any],
        has_pending_requirement_sdlc_agent_state: Callable[[], bool] = lambda: False,
        get_selected_agent_mode: Callable[[], str] = lambda: "auto",
    ) -> None:
        self.config = config
        self.detect_keyword_intent_fn = detect_keyword_intent_fn
        self.rag_service_available = rag_service_available
        self.jira_available = jira_available
        self.coze_client = coze_client
        self.use_mcp = use_mcp
        self.mcp_integration = mcp_integration
        self.jira_tool = jira_tool
        self.get_cached_intent = get_cached_intent
        self.cache_intent = cache_intent
        self.initialize_intent_detector = initialize_intent_detector
        self.has_pending_requirement_sdlc_agent_state = has_pending_requirement_sdlc_agent_state
        self.get_selected_agent_mode = get_selected_agent_mode

    def detect_intent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Detect the next intent for the provided agent state."""
        raw_user_input = state.get("user_input", "")
        user_input = raw_user_input.lower()
        messages = state.get("messages", [])
        logger.debug("Detecting intent for input: '%s...'", user_input[:50])

        if self.get_selected_agent_mode() == "requirement_sdlc_agent":
            state["intent"] = "requirement_sdlc_agent"
            logger.debug("Intent: requirement_sdlc_agent (explicit agent mode)")
            return state

        keyword_intent = self.detect_keyword_intent_fn(
            raw_user_input,
            rag_service_available=self.rag_service_available,
            jira_available=bool(self.jira_available),
            coze_enabled=self.config.COZE_ENABLED,
        )
        if keyword_intent == "general_chat":
            state["intent"] = keyword_intent
            logger.debug("Intent: %s (general-chat escape hatch)", keyword_intent)
            return state

        if self.has_pending_requirement_sdlc_agent_state():
            state["intent"] = "requirement_sdlc_agent"
            logger.debug("Intent: requirement_sdlc_agent (pending staged agent state)")
            return state

        if keyword_intent:
            state["intent"] = keyword_intent
            logger.debug("Intent: %s (keyword routing)", keyword_intent)
            return state

        if self.config.INTENT_USE_LLM:
            try:
                cached_result = self.get_cached_intent(user_input)
                if cached_result:
                    state["intent"] = cached_result.get("intent", "general_chat")
                    logger.debug("Intent: %s (from cache)", state["intent"])
                    return state

                intent_detector = self.initialize_intent_detector()
                if intent_detector:
                    conversation_context = self._build_conversation_context(messages)
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    future = executor.submit(
                        intent_detector.detect_intent,
                        user_input,
                        conversation_context,
                    )
                    try:
                        llm_result = future.result(timeout=self.config.INTENT_LLM_TIMEOUT)
                        confidence = llm_result.get("confidence", 0.0)
                        if confidence >= self.config.INTENT_CONFIDENCE_THRESHOLD:
                            detected_intent = llm_result.get("intent", "general_chat")
                            state["intent"] = detected_intent
                            self.cache_intent(user_input, llm_result)
                            logger.info(
                                "Intent: %s (LLM detection, confidence: %.2f, reasoning: %s)",
                                detected_intent,
                                confidence,
                                llm_result.get("reasoning", "N/A")[:50],
                            )
                            return state
                        logger.debug(
                            "LLM confidence %.2f below threshold %s, falling back to general_chat",
                            confidence,
                            self.config.INTENT_CONFIDENCE_THRESHOLD,
                        )
                    except concurrent.futures.TimeoutError:
                        future.cancel()
                        logger.warning(
                            "Intent detection timeout after %ss, falling back to general_chat",
                            self.config.INTENT_LLM_TIMEOUT,
                        )
                    except Exception as error:
                        logger.warning(
                            "Error during LLM intent detection: %s, falling back to general_chat",
                            error,
                        )
                    finally:
                        executor.shutdown(wait=False, cancel_futures=True)
                else:
                    logger.debug("Intent detector not available, falling back to general_chat")
            except Exception as error:
                logger.warning(
                    "Unexpected error in LLM intent detection: %s, falling back to general_chat",
                    error,
                )

        state["intent"] = "general_chat"
        logger.debug("Intent: general_chat (default fallback)")
        return state

    def route_after_intent(self, state: Dict[str, Any]) -> str:
        """Choose the next graph node after intent detection."""
        intent = state.get("intent", "general_chat")

        if intent == "requirement_sdlc_agent":
            return "requirement_sdlc_agent"

        if intent in {"general_chat", "rag_query", "coze_agent"}:
            if intent == "coze_agent":
                if (
                    self.config.COZE_ENABLED
                    and self.coze_client
                    and self.coze_client.is_configured()
                ):
                    return "coze_agent"
                logger.warning(
                    "Coze agent intent detected but Coze is not properly configured - "
                    "falling back to general_chat"
                )
                return "general_chat"
            return intent

        has_jira_tool = False
        if intent == "jira_creation":
            if self.jira_tool:
                has_jira_tool = True
            elif self.use_mcp and self.mcp_integration:
                if self.mcp_integration._initialized:
                    has_jira_tool = self.mcp_integration.has_tool("create_jira_issue")
                else:
                    has_jira_tool = True

        if intent == "jira_creation" and has_jira_tool:
            return "jira_creation"
        if intent == "rag_query":
            return "rag_query"
        return "general_chat"

    def _build_conversation_context(self, messages):
        if not messages:
            return None
        recent_messages = []
        for msg in messages[-5:]:
            if isinstance(msg, HumanMessage):
                recent_messages.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                recent_messages.append(f"Assistant: {msg.content}")
        return recent_messages or None
