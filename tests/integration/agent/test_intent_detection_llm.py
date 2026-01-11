"""
Integration tests for LLM-based intent detection.

Tests the hybrid intent detection system with LLM enabled for ambiguous cases.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import json
import concurrent.futures

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.agent_graph import ChatbotAgent, AgentState
from src.services.intent_detector import IntentDetector
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.intent_detection_llm')


@pytest.mark.agent
@pytest.mark.integration
class TestLLMBasedIntentDetection:
    """Integration tests for LLM-based intent detection."""
    
    @pytest.fixture
    def agent(self):
        """Create a ChatbotAgent instance with LLM-based detection enabled."""
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.OPENAI_MODEL = "gpt-3.5-turbo"
            mock_config.USE_MCP = False
            mock_config.COZE_ENABLED = False
            mock_config.INTENT_USE_LLM = True  # Enable LLM-based detection
            mock_config.INTENT_LLM_TEMPERATURE = 0.1
            mock_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            mock_config.INTENT_LLM_TIMEOUT = 5.0
            
            with patch('src.agent.agent_graph.ChatOpenAI'):
                agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=False,
                    use_mcp=False
                )
                return agent
    
    @pytest.fixture
    def mock_intent_detector(self):
        """Create a mock IntentDetector."""
        mock_detector = Mock(spec=IntentDetector)
        return mock_detector
    
    def test_keyword_match_bypasses_llm(self, agent):
        """Test that clear keyword matches bypass LLM detection."""
        state: AgentState = {
            "messages": [],
            "user_input": "create a jira ticket",  # Clear keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('config.config.Config') as mock_config, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            mock_config.INTENT_USE_LLM = True
            mock_agent_config.INTENT_USE_LLM = True
            # Mock jira_tool to simulate capability
            agent.jira_tool = Mock()
            
            result_state = agent._detect_intent(state)
            
            # Should detect jira_creation via keywords (fast path)
            assert result_state["intent"] == "jira_creation"
            # Intent detector should not be initialized (lazy loading)
            assert hasattr(agent, 'intent_detector')
            assert agent.intent_detector is None
    
    def test_ambiguous_case_uses_llm(self, agent, mock_intent_detector):
        """Test that ambiguous cases use LLM detection."""
        state: AgentState = {
            "messages": [],
            # Avoid substring matches for general_chat keywords like "assist" (in "assistance") or "hi" (in "this")
            "user_input": "Could you handle my request regarding account settings?",  # No clear keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        # Mock LLM response
        mock_intent_detector.detect_intent.return_value = {
            "intent": "general_chat",
            "confidence": 0.8,
            "reasoning": "User needs general assistance"
        }
        
        # Ensure cache is initialized
        if not hasattr(agent, '_intent_cache'):
            agent._intent_cache = {}
        
        # Patch Config class to enable LLM detection - must patch where it's imported
        with patch('src.agent.agent_graph.Config') as mock_config:
            # Set all required Config attributes
            mock_config.INTENT_USE_LLM = True
            mock_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            mock_config.INTENT_LLM_TIMEOUT = 5.0
            # Ensure other Config attributes exist to avoid AttributeError
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.OPENAI_MODEL = "gpt-3.5-turbo"
            
            # Mock the intent detector initialization to return mock directly
            def mock_init_detector():
                return mock_intent_detector
            
            with patch.object(agent, '_initialize_intent_detector', side_effect=mock_init_detector):
                result_state = agent._detect_intent(state)
                
                # Should use LLM detection
                assert result_state["intent"] == "general_chat"
                # Verify LLM was called
                assert mock_intent_detector.detect_intent.called, "LLM detect_intent should have been called"
                mock_intent_detector.detect_intent.assert_called_once()
    
    def test_llm_low_confidence_fallback(self, agent, mock_intent_detector):
        """Test that low confidence LLM results fallback to general_chat."""
        state: AgentState = {
            "messages": [],
            "user_input": "ambiguous query",  # No keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        # Mock LLM response with low confidence
        mock_intent_detector.detect_intent.return_value = {
            "intent": "rag_query",
            "confidence": 0.5,  # Below threshold
            "reasoning": "Uncertain detection"
        }
        
        with patch('config.config.Config') as mock_config, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            mock_config.INTENT_USE_LLM = True
            mock_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            mock_agent_config.INTENT_USE_LLM = True
            mock_agent_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            mock_agent_config.INTENT_LLM_TIMEOUT = 5.0
            
            with patch.object(agent, '_initialize_intent_detector', return_value=mock_intent_detector):
                result_state = agent._detect_intent(state)
                
                # Should fallback to general_chat due to low confidence
                assert result_state["intent"] == "general_chat"
    
    def test_llm_timeout_handling(self, agent, mock_intent_detector):
        """Test that LLM timeout falls back to general_chat."""
        state: AgentState = {
            "messages": [],
            "user_input": "slow query",  # No keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        # Mock LLM to timeout
        mock_intent_detector.detect_intent.side_effect = concurrent.futures.TimeoutError()
        
        with patch('config.config.Config') as mock_config, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            mock_config.INTENT_USE_LLM = True
            mock_config.INTENT_LLM_TIMEOUT = 1.0
            mock_agent_config.INTENT_USE_LLM = True
            mock_agent_config.INTENT_LLM_TIMEOUT = 1.0
            mock_agent_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            
            with patch.object(agent, '_initialize_intent_detector', return_value=mock_intent_detector):
                result_state = agent._detect_intent(state)
                
                # Should fallback to general_chat on timeout
                assert result_state["intent"] == "general_chat"
    
    def test_llm_error_handling(self, agent, mock_intent_detector):
        """Test that LLM errors fall back to general_chat."""
        state: AgentState = {
            "messages": [],
            "user_input": "error query",  # No keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        # Mock LLM to raise error
        mock_intent_detector.detect_intent.side_effect = Exception("LLM API error")
        
        with patch('config.config.Config') as mock_config, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            mock_config.INTENT_USE_LLM = True
            mock_agent_config.INTENT_USE_LLM = True
            mock_agent_config.INTENT_LLM_TIMEOUT = 5.0
            mock_agent_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            
            with patch.object(agent, '_initialize_intent_detector', return_value=mock_intent_detector):
                result_state = agent._detect_intent(state)
                
                # Should fallback to general_chat on error
                assert result_state["intent"] == "general_chat"
    
    def test_intent_caching(self, agent, mock_intent_detector):
        """Test that intent detection results are cached."""
        state: AgentState = {
            "messages": [],
            "user_input": "cached query",  # No keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        # Mock LLM response
        mock_intent_detector.detect_intent.return_value = {
            "intent": "rag_query",
            "confidence": 0.9,
            "reasoning": "Cached result"
        }
        
        # Patch Config in all places where it's used
        with patch('config.config.Config') as mock_config_module, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            # Set all required config values
            for mock_config in [mock_config_module, mock_agent_config]:
                mock_config.INTENT_USE_LLM = True
                mock_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
                mock_config.INTENT_LLM_TIMEOUT = 5.0
            
            # Ensure cache is initialized
            if not hasattr(agent, '_intent_cache'):
                agent._intent_cache = {}
            
            with patch.object(agent, '_initialize_intent_detector', return_value=mock_intent_detector):
                # First call - should call LLM
                result_state1 = agent._detect_intent(state)
                assert result_state1["intent"] == "rag_query", f"Expected rag_query, got {result_state1['intent']}"
                assert mock_intent_detector.detect_intent.call_count == 1, "LLM should be called once on first request"
                
                # Reset call count to verify cache works
                mock_intent_detector.detect_intent.reset_mock()
                
                # Second call with same input - should use cache (no LLM call)
                result_state2 = agent._detect_intent(state)
                assert result_state2["intent"] == "rag_query", f"Expected rag_query from cache, got {result_state2['intent']}"
                # Should not be called again (cache hit)
                assert mock_intent_detector.detect_intent.call_count == 0, "LLM should not be called again due to cache"
    
    def test_conversation_context_passed_to_llm(self, agent, mock_intent_detector):
        """Test that conversation context is passed to LLM detection."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        state: AgentState = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
                HumanMessage(content="I need help")
            ],
            # Avoid substring match of general_chat keyword "hi" inside words like "something"
            "user_input": "continue please",  # No keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        mock_intent_detector.detect_intent.return_value = {
            "intent": "general_chat",
            "confidence": 0.8,
            "reasoning": "Context-aware detection"
        }
        
        # Patch Config class to enable LLM detection
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.INTENT_USE_LLM = True
            mock_config.INTENT_CONFIDENCE_THRESHOLD = 0.7
            mock_config.INTENT_LLM_TIMEOUT = 5.0
            
            # Ensure cache is initialized
            if not hasattr(agent, '_intent_cache'):
                agent._intent_cache = {}
            
            # Mock the intent detector initialization to bypass Config check and return mock directly
            def mock_init_detector():
                return mock_intent_detector
            
            with patch.object(agent, '_initialize_intent_detector', side_effect=mock_init_detector):
                result_state = agent._detect_intent(state)
                
                # Verify context was passed (check call arguments)
                assert mock_intent_detector.detect_intent.called, "LLM detect_intent should have been called"
                call_args = mock_intent_detector.detect_intent.call_args
                assert call_args is not None
                # Check if conversation_context was passed (either as positional or keyword arg)
                args, kwargs = call_args
                assert len(args) >= 1  # user_input is first arg
                # Context might be in args[1] or kwargs['conversation_context']
                assert len(args) > 1 or 'conversation_context' in kwargs
    
    def test_llm_disabled_fallback(self, agent):
        """Test that when LLM is disabled, ambiguous cases fallback to general_chat."""
        state: AgentState = {
            "messages": [],
            "user_input": "ambiguous query with no keywords",  # No keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('config.config.Config') as mock_config, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            mock_config.INTENT_USE_LLM = False  # Disable LLM
            mock_agent_config.INTENT_USE_LLM = False
            
            result_state = agent._detect_intent(state)
            
            # Should fallback to general_chat when LLM is disabled
            assert result_state["intent"] == "general_chat"
            # Intent detector should not be initialized
            assert hasattr(agent, 'intent_detector')
            assert agent.intent_detector is None
    
    def test_hybrid_approach_keyword_first(self, agent):
        """Test that hybrid approach checks keywords first before LLM."""
        state: AgentState = {
            "messages": [],
            "user_input": "create jira",  # Clear keyword match
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "coze_result": None,
            "conversation_history": [],
            "next_action": None
        }
        
        with patch('config.config.Config') as mock_config, \
             patch('src.agent.agent_graph.Config') as mock_agent_config:
            mock_config.INTENT_USE_LLM = True
            mock_agent_config.INTENT_USE_LLM = True
            agent.jira_tool = Mock()  # Simulate Jira capability
            
            result_state = agent._detect_intent(state)
            
            # Should detect via keywords (fast path), not LLM
            assert result_state["intent"] == "jira_creation"
            # Intent detector should not be initialized (lazy loading, not needed)
            assert hasattr(agent, 'intent_detector')
            assert agent.intent_detector is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

