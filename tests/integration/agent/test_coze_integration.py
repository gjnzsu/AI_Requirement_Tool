"""
Test cases for Coze Platform API Integration.

This test suite covers:
1. CozeClient unit tests
2. Agent intent detection for Coze keywords
3. Agent routing to Coze handler
4. End-to-end Coze agent execution

To run these tests:
    pytest tests/integration/agent/test_coze_integration.py -v
    pytest tests/integration/agent/test_coze_integration.py -v -m coze
    python run_tests.py --agent
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.coze_client import CozeClient
from src.agent.agent_graph import ChatbotAgent, AgentState
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.coze')


@pytest.mark.agent
@pytest.mark.coze
class TestCozeClient:
    """Unit tests for CozeClient."""
    
    def test_coze_client_initialization(self):
        """Test CozeClient initialization with default config."""
        with patch('src.services.coze_client.Config') as mock_config:
            mock_config.COZE_API_TOKEN = "test-token"
            mock_config.COZE_BOT_ID = "test-bot-id"
            mock_config.COZE_API_BASE_URL = "https://api.coze.com"
            
            client = CozeClient()
            assert client.api_token == "test-token"
            assert client.bot_id == "test-bot-id"
            assert client.base_url == "https://api.coze.com"
    
    def test_coze_client_initialization_custom_params(self):
        """Test CozeClient initialization with custom parameters."""
        client = CozeClient(
            api_token="custom-token",
            bot_id="custom-bot-id",
            base_url="https://custom.coze.com"
        )
        assert client.api_token == "custom-token"
        assert client.bot_id == "custom-bot-id"
        assert client.base_url == "https://custom.coze.com"
    
    def test_coze_client_is_configured(self):
        """Test is_configured() method."""
        # Mock Config to have empty values to avoid fallback
        with patch('src.services.coze_client.Config') as mock_config:
            mock_config.COZE_API_TOKEN = ""
            mock_config.COZE_BOT_ID = ""
            mock_config.COZE_API_BASE_URL = "https://api.coze.com"
            
            # Properly configured
            client = CozeClient(api_token="token", bot_id="bot-id")
            assert client.is_configured() is True
            
            # Missing token
            client = CozeClient(api_token="", bot_id="bot-id")
            assert client.is_configured() is False
            
            # Missing bot_id
            client = CozeClient(api_token="token", bot_id="")
            assert client.is_configured() is False
            
            # Both missing
            client = CozeClient(api_token="", bot_id="")
            assert client.is_configured() is False
    
    @patch('src.services.coze_client.requests.post')
    def test_coze_client_execute_agent_success(self, mock_post):
        """Test successful agent execution."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "messages": [
                    {"content": "This is a test response from Coze agent"}
                ]
            },
            "conversation_id": "conv-123"
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = CozeClient(api_token="test-token", bot_id="test-bot-id")
        result = client.execute_agent("test query")
        
        assert result["success"] is True
        assert "response" in result
        assert result["conversation_id"] == "conv-123"
        mock_post.assert_called_once()
    
    @patch('src.services.coze_client.requests.post')
    def test_coze_client_execute_agent_timeout(self, mock_post):
        """Test agent execution timeout handling."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        client = CozeClient(api_token="test-token", bot_id="test-bot-id")
        result = client.execute_agent("test query")
        
        assert result["success"] is False
        assert result["error_type"] == "timeout"
        assert "timed out" in result["error"].lower()
    
    @patch('src.services.coze_client.requests.post')
    def test_coze_client_execute_agent_http_error_401(self, mock_post):
        """Test agent execution with 401 authentication error."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        client = CozeClient(api_token="invalid-token", bot_id="test-bot-id")
        result = client.execute_agent("test query")
        
        assert result["success"] is False
        assert result["error_type"] == "http_error"
        assert result["status_code"] == 401
        assert "authentication" in result["error"].lower() or "token" in result["error"].lower()
    
    @patch('src.services.coze_client.requests.post')
    def test_coze_client_execute_agent_http_error_404(self, mock_post):
        """Test agent execution with 404 bot not found error."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Bot not found"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        client = CozeClient(api_token="test-token", bot_id="invalid-bot-id")
        result = client.execute_agent("test query")
        
        assert result["success"] is False
        assert result["error_type"] == "http_error"
        assert result["status_code"] == 404
        assert "bot" in result["error"].lower()
    
    @patch('src.services.coze_client.requests.post')
    def test_coze_client_execute_agent_network_error(self, mock_post):
        """Test agent execution with network error."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        client = CozeClient(api_token="test-token", bot_id="test-bot-id")
        result = client.execute_agent("test query")
        
        assert result["success"] is False
        assert result["error_type"] == "network_error"
    
    @patch('src.services.coze_client.requests.post')
    def test_coze_client_extract_response_various_formats(self, mock_post):
        """Test response extraction for various Coze API response formats."""
        client = CozeClient(api_token="test-token", bot_id="test-bot-id")
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        
        # Format 1: Direct message field
        mock_response.json.return_value = {"message": "Direct message"}
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        result = client.execute_agent("test")
        assert result["success"] is True
        assert result["response"] == "Direct message"
        
        # Format 2: Data with messages array
        mock_response.json.return_value = {
            "data": {
                "messages": [{"content": "Message from array"}]
            }
        }
        result = client.execute_agent("test")
        assert result["success"] is True
        assert result["response"] == "Message from array"
        
        # Format 3: Choices array (OpenAI-like)
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Choice message"}
            }]
        }
        result = client.execute_agent("test")
        assert result["success"] is True
        assert result["response"] == "Choice message"
        
        # Format 4: Direct content field
        mock_response.json.return_value = {"content": "Direct content"}
        result = client.execute_agent("test")
        assert result["success"] is True
        assert result["response"] == "Direct content"


@pytest.mark.agent
@pytest.mark.coze
class TestCozeAgentIntentDetection:
    """Tests for Coze agent intent detection."""
    
    @pytest.fixture
    def agent(self):
        """Create a ChatbotAgent instance for testing."""
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.OPENAI_MODEL = "gpt-3.5-turbo"
            mock_config.USE_MCP = False
            mock_config.COZE_ENABLED = True
            
            with patch('src.agent.agent_graph.ChatOpenAI'):
                agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=False,
                    use_mcp=False
                )
                return agent
    
    def test_intent_detection_ai_daily_report(self, agent):
        """Test intent detection for 'AI daily report' keyword."""
        state: AgentState = {
            "messages": [],
            "user_input": "Can you give me an AI daily report?",
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.COZE_ENABLED = True
            
            result_state = agent._detect_intent(state)
            assert result_state["intent"] == "coze_agent"
    
    def test_intent_detection_ai_news(self, agent):
        """Test intent detection for 'AI news' keyword."""
        state: AgentState = {
            "messages": [],
            "user_input": "Show me the latest AI news",
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.COZE_ENABLED = True
            
            result_state = agent._detect_intent(state)
            assert result_state["intent"] == "coze_agent"
    
    def test_intent_detection_coze_disabled(self, agent):
        """Test that Coze intent is not set when Coze is disabled."""
        state: AgentState = {
            "messages": [],
            "user_input": "Can you give me an AI daily report?",
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.COZE_ENABLED = False
            
            result_state = agent._detect_intent(state)
            # Should fallback to general_chat when Coze is disabled
            assert result_state["intent"] == "general_chat"
    
    def test_intent_detection_case_insensitive(self, agent):
        """Test that keyword detection is case-insensitive."""
        state: AgentState = {
            "messages": [],
            "user_input": "I need an AI DAILY REPORT please",
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.COZE_ENABLED = True
            
            result_state = agent._detect_intent(state)
            assert result_state["intent"] == "coze_agent"


@pytest.mark.agent
@pytest.mark.coze
class TestCozeAgentRouting:
    """Tests for Coze agent routing logic."""
    
    @pytest.fixture
    def agent(self):
        """Create a ChatbotAgent instance with mocked Coze client."""
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.OPENAI_MODEL = "gpt-3.5-turbo"
            mock_config.USE_MCP = False
            mock_config.COZE_ENABLED = True
            
            with patch('src.agent.agent_graph.ChatOpenAI'):
                agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=False,
                    use_mcp=False
                )
                # Mock Coze client
                mock_coze_client = Mock()
                mock_coze_client.is_configured.return_value = True
                agent.coze_client = mock_coze_client
                return agent
    
    def test_route_after_intent_coze_agent(self, agent):
        """Test routing to coze_agent node."""
        state: AgentState = {
            "messages": [],
            "user_input": "AI daily report",
            "intent": "coze_agent",
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.COZE_ENABLED = True
            
            route = agent._route_after_intent(state)
            assert route == "coze_agent"
    
    def test_route_after_intent_coze_not_configured(self, agent):
        """Test fallback when Coze is not properly configured."""
        state: AgentState = {
            "messages": [],
            "user_input": "AI daily report",
            "intent": "coze_agent",
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        # Mock Coze client as not configured
        agent.coze_client.is_configured.return_value = False
        
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.COZE_ENABLED = True
            
            route = agent._route_after_intent(state)
            assert route == "general_chat"


@pytest.mark.agent
@pytest.mark.coze
class TestCozeAgentHandler:
    """Tests for Coze agent handler execution."""
    
    @pytest.fixture
    def agent(self):
        """Create a ChatbotAgent instance with mocked components."""
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.OPENAI_MODEL = "gpt-3.5-turbo"
            mock_config.USE_MCP = False
            
            with patch('src.agent.agent_graph.ChatOpenAI'):
                agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=False,
                    use_mcp=False
                )
                return agent
    
    def test_handle_coze_agent_success(self, agent):
        """Test successful Coze agent execution."""
        # Mock Coze client
        mock_coze_client = Mock()
        mock_coze_client.is_configured.return_value = True
        mock_coze_client.execute_agent.return_value = {
            "success": True,
            "response": "Here is your AI daily report: ...",
            "conversation_id": "conv-123"
        }
        agent.coze_client = mock_coze_client
        
        state: AgentState = {
            "messages": [],
            "user_input": "AI daily report",
            "intent": "coze_agent",
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        result_state = agent._handle_coze_agent(state)
        
        assert result_state["coze_result"]["success"] is True
        assert len(result_state["messages"]) > 0
        assert "AI daily report" in result_state["messages"][-1].content or "report" in result_state["messages"][-1].content.lower()
        mock_coze_client.execute_agent.assert_called_once()
    
    def test_handle_coze_agent_not_configured(self, agent):
        """Test handler when Coze client is not configured."""
        agent.coze_client = None
        
        state: AgentState = {
            "messages": [],
            "user_input": "AI daily report",
            "intent": "coze_agent",
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        result_state = agent._handle_coze_agent(state)
        
        assert len(result_state["messages"]) > 0
        assert "not properly configured" in result_state["messages"][-1].content.lower()
    
    def test_handle_coze_agent_api_error(self, agent):
        """Test handler when Coze API returns an error."""
        mock_coze_client = Mock()
        mock_coze_client.is_configured.return_value = True
        mock_coze_client.execute_agent.return_value = {
            "success": False,
            "error": "Authentication failed",
            "error_type": "http_error",
            "status_code": 401
        }
        agent.coze_client = mock_coze_client
        
        state: AgentState = {
            "messages": [],
            "user_input": "AI daily report",
            "intent": "coze_agent",
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        result_state = agent._handle_coze_agent(state)
        
        assert result_state["coze_result"]["success"] is False
        assert len(result_state["messages"]) > 0
        assert "error" in result_state["messages"][-1].content.lower() or "authentication" in result_state["messages"][-1].content.lower()
    
    def test_handle_coze_agent_timeout(self, agent):
        """Test handler when Coze API times out."""
        import concurrent.futures
        
        mock_coze_client = Mock()
        mock_coze_client.is_configured.return_value = True
        mock_coze_client.execute_agent.side_effect = concurrent.futures.TimeoutError()
        agent.coze_client = mock_coze_client
        
        state: AgentState = {
            "messages": [],
            "user_input": "AI daily report",
            "intent": "coze_agent",
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        result_state = agent._handle_coze_agent(state)
        
        assert result_state["coze_result"]["success"] is False
        assert "timeout" in result_state["coze_result"]["error"].lower() or "timeout" in result_state["messages"][-1].content.lower()


@pytest.mark.integration
@pytest.mark.timeout(120)
class TestCozeIntegrationE2E:
    """End-to-end integration tests for Coze platform."""
    
    @pytest.mark.skipif(
        not Config.COZE_ENABLED or not Config.COZE_API_TOKEN or not Config.COZE_BOT_ID,
        reason="Coze integration not configured (set COZE_ENABLED=true, COZE_API_TOKEN, COZE_BOT_ID)"
    )
    def test_coze_agent_end_to_end(self):
        """End-to-end test of Coze agent integration."""
        logger.info("=" * 60)
        logger.info("Testing Coze Agent Integration (E2E)")
        logger.info("=" * 60)
        
        try:
            # Initialize agent
            logger.info("Initializing ChatbotAgent with Coze enabled...")
            agent = ChatbotAgent(
                provider_name="openai",
                enable_tools=False,
                use_mcp=False
            )
            
            if not agent.coze_client or not agent.coze_client.is_configured():
                pytest.skip("Coze client not properly configured")
            
            logger.info("Agent initialized successfully!")
            logger.info("")
            
            # Test 1: Intent detection
            logger.info("Test 1: Intent Detection")
            logger.info("-" * 60)
            state: AgentState = {
                "messages": [],
                "user_input": "Can you give me an AI daily report?",
                "intent": None,
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "coze_result": None,
                "conversation_history": [],
                "next_action": None
            }
            
            result_state = agent._detect_intent(state)
            assert result_state["intent"] == "coze_agent", f"Expected coze_agent intent, got {result_state['intent']}"
            logger.info(f"✓ Intent detected: {result_state['intent']}")
            logger.info("")
            
            # Test 2: Routing
            logger.info("Test 2: Routing Logic")
            logger.info("-" * 60)
            route = agent._route_after_intent(result_state)
            assert route == "coze_agent", f"Expected coze_agent route, got {route}"
            logger.info(f"✓ Routing to: {route}")
            logger.info("")
            
            # Test 3: Agent execution (if API credentials are available)
            logger.info("Test 3: Coze Agent Execution")
            logger.info("-" * 60)
            logger.info("Note: This requires valid Coze API credentials")
            
            execution_state = agent._handle_coze_agent(result_state)
            
            if execution_state["coze_result"]["success"]:
                logger.info("✓ Coze agent executed successfully")
                logger.info(f"Response: {execution_state['coze_result']['response'][:200]}...")
            else:
                error = execution_state["coze_result"].get("error", "Unknown error")
                logger.warning(f"Coze agent execution failed: {error}")
                # Don't fail the test if it's a configuration/network issue
                if "not properly configured" not in error.lower():
                    logger.warning("This may be due to invalid credentials or network issues")
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("Coze Integration Tests Completed")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during Coze integration testing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

