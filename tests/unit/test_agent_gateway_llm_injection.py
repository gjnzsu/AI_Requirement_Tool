from unittest.mock import Mock, patch


class FakeGatewayLLM:
    model = "gpt-5.4"

    def invoke(self, messages):
        return Mock(content="ok")

    def generate_response(self, *args, **kwargs):
        return "ok"

    def supports_json_mode(self):
        return True

    def get_provider_name(self):
        return "gateway"


def test_chatbot_agent_reuses_injected_llm_without_embedded_initialization():
    injected_llm = FakeGatewayLLM()

    with patch("src.agent.agent_graph.ChatOpenAI") as chat_openai, \
        patch("src.agent.agent_graph.JiraTool"), \
        patch("src.agent.agent_graph.ConfluenceTool"), \
        patch("src.agent.agent_graph.MCPIntegration"), \
        patch("src.agent.agent_graph.Config") as mock_config:
        mock_config.USE_MCP = False
        mock_config.COZE_ENABLED = False
        mock_config.INTENT_USE_LLM = True
        mock_config.INTENT_LLM_TEMPERATURE = 0.1
        mock_config.JIRA_URL = "https://example.atlassian.net"
        mock_config.JIRA_EMAIL = "user@example.com"
        mock_config.JIRA_API_TOKEN = "token"
        mock_config.JIRA_PROJECT_KEY = "PROJ"
        mock_config.CONFLUENCE_URL = ""
        mock_config.CONFLUENCE_SPACE_KEY = "TEAM"

        from src.agent.agent_graph import ChatbotAgent

        agent = ChatbotAgent(
            provider_name="openai",
            enable_tools=False,
            llm_provider=injected_llm,
            use_mcp=False,
        )

    chat_openai.assert_not_called()
    assert agent.llm is injected_llm
    assert agent.chat_response_service.llm_provider is injected_llm
    assert agent.requirement_sdlc_agent_service.llm_provider is injected_llm


def test_chatbot_agent_intent_detector_reuses_injected_llm():
    injected_llm = FakeGatewayLLM()

    with patch("src.agent.agent_graph.ChatOpenAI"), \
        patch("src.agent.agent_graph.JiraTool"), \
        patch("src.agent.agent_graph.ConfluenceTool"), \
        patch("src.agent.agent_graph.MCPIntegration"), \
        patch("src.llm.LLMRouter.get_provider") as get_provider, \
        patch("src.agent.agent_graph.Config") as mock_config:
        mock_config.USE_MCP = False
        mock_config.COZE_ENABLED = False
        mock_config.INTENT_USE_LLM = True
        mock_config.INTENT_LLM_TEMPERATURE = 0.1
        mock_config.JIRA_URL = "https://example.atlassian.net"
        mock_config.JIRA_EMAIL = "user@example.com"
        mock_config.JIRA_API_TOKEN = "token"
        mock_config.JIRA_PROJECT_KEY = "PROJ"
        mock_config.CONFLUENCE_URL = ""
        mock_config.CONFLUENCE_SPACE_KEY = "TEAM"

        from src.agent.agent_graph import ChatbotAgent

        agent = ChatbotAgent(
            provider_name="openai",
            enable_tools=False,
            llm_provider=injected_llm,
            use_mcp=False,
        )
        detector = agent._initialize_intent_detector()

    get_provider.assert_not_called()
    assert detector.llm_provider is injected_llm
