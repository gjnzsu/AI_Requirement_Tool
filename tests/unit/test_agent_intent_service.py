from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

from src.services.agent_intent_service import AgentIntentService
from src.agent.intent_routing import detect_keyword_intent


class FakeConfig:
    COZE_ENABLED = True
    INTENT_USE_LLM = True
    INTENT_LLM_TIMEOUT = 1.0
    INTENT_CONFIDENCE_THRESHOLD = 0.7


def test_detect_intent_uses_cache_before_detector():
    cached_result = {"intent": "rag_query", "confidence": 0.9}
    get_cached_intent = Mock(return_value=cached_result)
    initialize_intent_detector = Mock()
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value=None),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=object(),
        get_cached_intent=get_cached_intent,
        cache_intent=Mock(),
        initialize_intent_detector=initialize_intent_detector,
    )

    state = {"user_input": "tell me about PROJ-1", "messages": [], "intent": None}
    result = service.detect_intent(state)

    assert result["intent"] == "rag_query"
    initialize_intent_detector.assert_not_called()


def test_detect_intent_uses_llm_detector_and_caches_high_confidence_result():
    detector = Mock()
    detector.detect_intent.return_value = {
        "intent": "jira_creation",
        "confidence": 0.95,
        "reasoning": "looks like creation",
    }
    cache_intent = Mock()
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value=None),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=object(),
        get_cached_intent=Mock(return_value=None),
        cache_intent=cache_intent,
        initialize_intent_detector=Mock(return_value=detector),
    )

    state = {
        "user_input": "please create a jira for login",
        "messages": [HumanMessage(content="Need a login ticket"), AIMessage(content="Okay")],
        "intent": None,
    }
    result = service.detect_intent(state)

    assert result["intent"] == "jira_creation"
    cache_intent.assert_called_once()


def test_route_after_intent_falls_back_to_general_chat_when_coze_unavailable():
    coze_client = Mock()
    coze_client.is_configured.return_value = False
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(),
        rag_service_available=False,
        jira_available=True,
        coze_client=coze_client,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=object(),
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
    )

    route = service.route_after_intent({"intent": "coze_agent"})

    assert route == "general_chat"


def test_route_after_intent_returns_requirement_sdlc_agent():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=False),
    )

    route = service.route_after_intent({"intent": "requirement_sdlc_agent"})

    assert route == "requirement_sdlc_agent"


def test_detect_intent_short_circuits_to_agent_when_confirmation_pending():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value=None),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=True),
    )

    state = service.detect_intent({"user_input": "approve", "messages": []})

    assert state["intent"] == "requirement_sdlc_agent"


def test_detect_intent_short_circuits_to_agent_when_analysis_follow_up_pending():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value=None),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=True),
    )

    state = service.detect_intent(
        {"user_input": "the business value is audit readiness", "messages": []}
    )

    assert state["intent"] == "requirement_sdlc_agent"


def test_detect_intent_allows_general_chat_escape_hatch_when_pending_in_auto_mode():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value="general_chat"),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=True),
        get_selected_agent_mode=Mock(return_value="auto"),
    )

    state = service.detect_intent({"user_input": "who are you?", "messages": []})

    assert state["intent"] == "general_chat"


def test_detect_intent_honors_explicit_requirement_sdlc_agent_mode():
    service = AgentIntentService(
        config=FakeConfig,
        detect_keyword_intent_fn=Mock(return_value=None),
        rag_service_available=True,
        jira_available=True,
        coze_client=None,
        use_mcp=False,
        mcp_integration=None,
        jira_tool=None,
        get_cached_intent=Mock(),
        cache_intent=Mock(),
        initialize_intent_detector=Mock(),
        has_pending_requirement_sdlc_agent_state=Mock(return_value=False),
        get_selected_agent_mode=Mock(return_value="requirement_sdlc_agent"),
    )

    state = service.detect_intent({"user_input": "hello", "messages": []})

    assert state["intent"] == "requirement_sdlc_agent"


def test_detect_keyword_intent_treats_model_identity_question_as_general_chat():
    intent = detect_keyword_intent(
        "which llm model are you using?",
        rag_service_available=True,
        jira_available=True,
        coze_enabled=True,
    )

    assert intent == "general_chat"
