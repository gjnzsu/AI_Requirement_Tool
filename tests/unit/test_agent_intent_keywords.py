"""
Unit tests for ChatbotAgent keyword-based intent detection.

Tests the keyword-based intent detection logic in _detect_intent method,
including the new Jira/Confluence knowledge lookup patterns.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger('test.agent_intent_keywords')


@pytest.fixture
def mock_agent_with_rag():
    """Create a ChatbotAgent with mocked dependencies and RAG enabled."""
    with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm, \
         patch('src.agent.agent_graph.JiraTool'), \
         patch('src.agent.agent_graph.ConfluenceTool'), \
         patch('src.agent.agent_graph.IntentDetector'), \
         patch('src.agent.agent_graph.MCPIntegration'), \
         patch('src.agent.agent_graph.Config') as mock_config:
        
        mock_config.OPENAI_API_KEY = "test-key"
        mock_config.USE_MCP = False
        mock_config.JIRA_URL = "https://test.atlassian.net"
        mock_config.CONFLUENCE_URL = None
        mock_config.COZE_ENABLED = False
        mock_config.INTENT_USE_LLM = False  # Disable LLM-based intent detection
        
        # Create mock RAG service
        mock_rag = Mock()
        
        from src.agent.agent_graph import ChatbotAgent
        agent = ChatbotAgent(
            provider_name="openai",
            enable_tools=True,
            rag_service=mock_rag,
            use_mcp=False
        )
        
        yield agent  # Use yield to keep patches active during test


@pytest.fixture
def mock_agent_without_rag():
    """Create a ChatbotAgent without RAG service."""
    with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm, \
         patch('src.agent.agent_graph.JiraTool'), \
         patch('src.agent.agent_graph.ConfluenceTool'), \
         patch('src.agent.agent_graph.IntentDetector'), \
         patch('src.agent.agent_graph.MCPIntegration'), \
         patch('src.agent.agent_graph.Config') as mock_config:
        
        mock_config.OPENAI_API_KEY = "test-key"
        mock_config.USE_MCP = False
        mock_config.JIRA_URL = "https://test.atlassian.net"
        mock_config.CONFLUENCE_URL = None
        mock_config.COZE_ENABLED = False
        mock_config.INTENT_USE_LLM = False
        
        from src.agent.agent_graph import ChatbotAgent
        agent = ChatbotAgent(
            provider_name="openai",
            enable_tools=True,
            rag_service=None,  # No RAG
            use_mcp=False
        )
        
        yield agent  # Use yield to keep patches active during test


@pytest.mark.unit
class TestRAGKeywordIntentDetection:
    """Tests for RAG keyword-based intent detection."""
    
    def test_jira_key_pattern_routes_to_rag(self, mock_agent_with_rag):
        """Test that Jira key pattern (e.g., PROJ-123) routes to rag_query."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "What was the acceptance criteria for PROJ-123?",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_jira_key_with_various_formats(self, mock_agent_with_rag):
        """Test Jira key pattern matches various valid formats."""
        agent = mock_agent_with_rag
        
        test_cases = [
            "Show me details of AUTH-001",
            "What is TEST-9999 about?",
            "Find information about LONGPROJ-1",
            "Tell me about AB-12",
        ]
        
        for user_input in test_cases:
            state = {"user_input": user_input, "messages": [], "intent": None}
            result = agent._detect_intent(state)
            assert result["intent"] == "rag_query", f"Failed for: {user_input}"
    
    def test_jira_creation_not_routed_to_rag(self, mock_agent_with_rag):
        """Test that Jira creation requests are NOT routed to RAG even with key."""
        agent = mock_agent_with_rag
        
        # These should route to jira_creation, not rag_query
        creation_inputs = [
            "Create a Jira ticket similar to PROJ-123",
            "Create issue like AUTH-001",
            "New ticket based on TEST-456",
        ]
        
        for user_input in creation_inputs:
            state = {"user_input": user_input, "messages": [], "intent": None}
            result = agent._detect_intent(state)
            # Should be jira_creation, not rag_query
            assert result["intent"] == "jira_creation", f"Expected jira_creation for: {user_input}"
    
    def test_acceptance_criteria_keyword(self, mock_agent_with_rag):
        """Test 'acceptance criteria' keyword routes to RAG."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "What was the acceptance criteria for the auth feature?",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_business_value_keyword(self, mock_agent_with_rag):
        """Test 'business value' keyword routes to RAG."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "What was the business value of the login feature?",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_show_me_the_keyword(self, mock_agent_with_rag):
        """Test 'show me the' keyword routes to RAG."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "Show me the details of the authentication ticket",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_confluence_page_keyword(self, mock_agent_with_rag):
        """Test 'confluence page' keyword routes to RAG."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "Find the confluence page about user authentication",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_ticket_details_keyword(self, mock_agent_with_rag):
        """Test 'ticket details' keyword routes to RAG."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "I need the ticket details for the security fix",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_lookup_keyword(self, mock_agent_with_rag):
        """Test 'lookup' keyword routes to RAG."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "Lookup the previous sprint items",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "rag_query"
    
    def test_rag_query_requires_rag_service(self, mock_agent_without_rag):
        """Test that RAG keywords don't route to rag_query when RAG is unavailable."""
        agent = mock_agent_without_rag
        
        state = {
            "user_input": "What was the acceptance criteria for the feature?",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        # Should NOT be rag_query since RAG service is not available
        assert result["intent"] != "rag_query"


@pytest.mark.unit
class TestJiraCreationIntentDetection:
    """Tests for Jira creation intent detection (existing functionality)."""
    
    def test_create_jira_keyword(self, mock_agent_with_rag):
        """Test 'create jira' keyword routes to jira_creation."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "Create a jira ticket for the login bug",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "jira_creation"
    
    def test_new_ticket_keyword(self, mock_agent_with_rag):
        """Test 'new ticket' keyword routes to jira_creation."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "I need a new ticket for this feature",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "jira_creation"


@pytest.mark.unit
class TestGeneralChatIntentDetection:
    """Tests for general chat intent detection."""
    
    def test_greeting_routes_to_general_chat(self, mock_agent_with_rag):
        """Test greetings route to general_chat."""
        agent = mock_agent_with_rag
        
        greetings = ["Hello", "Hi there", "Hey", "Good morning"]
        
        for greeting in greetings:
            state = {"user_input": greeting, "messages": [], "intent": None}
            result = agent._detect_intent(state)
            assert result["intent"] == "general_chat", f"Failed for: {greeting}"
    
    def test_thanks_routes_to_general_chat(self, mock_agent_with_rag):
        """Test 'thanks' routes to general_chat."""
        agent = mock_agent_with_rag
        
        state = {
            "user_input": "Thanks for your help!",
            "messages": [],
            "intent": None
        }
        
        result = agent._detect_intent(state)
        
        assert result["intent"] == "general_chat"


@pytest.mark.unit  
class TestIntentDisambiguation:
    """Tests for distinguishing between similar intents."""
    
    def test_lookup_vs_creation_disambiguation(self, mock_agent_with_rag):
        """Test disambiguation between lookup and creation intents."""
        agent = mock_agent_with_rag
        
        # Lookup queries (should be rag_query)
        lookup_queries = [
            "What was the acceptance criteria for PROJ-123?",
            "Show me the details of AUTH-001",
            "Find information about the login ticket",
        ]
        
        # Creation queries (should be jira_creation)
        creation_queries = [
            "Create a ticket for the login feature",
            "Create a new Jira issue",
            "Make a ticket for the bug",
        ]
        
        for query in lookup_queries:
            state = {"user_input": query, "messages": [], "intent": None}
            result = agent._detect_intent(state)
            assert result["intent"] == "rag_query", f"Expected rag_query for: {query}"
        
        for query in creation_queries:
            state = {"user_input": query, "messages": [], "intent": None}
            result = agent._detect_intent(state)
            assert result["intent"] == "jira_creation", f"Expected jira_creation for: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

