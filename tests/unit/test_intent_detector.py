"""
Unit tests for IntentDetector service.

Tests the LLM-based intent detection logic with mocked LLM responses.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.intent_detector import IntentDetector
from src.llm import LLMProvider
from src.utils.logger import get_logger

logger = get_logger('test.intent_detector')


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, response: str = None):
        super().__init__(api_key="test-key", model="test-model")
        self.response = response or '{"intent": "general_chat", "confidence": 0.8, "reasoning": "Test"}'
        self.supports_json_mode_called = False
        self.generate_response_called = False
        self.last_temperature = None
    
    def generate_response(self, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.3, json_mode: bool = False) -> str:
        """Return mock response."""
        self.generate_response_called = True
        self.last_temperature = temperature
        return self.response
    
    def supports_json_mode(self) -> bool:
        """Return True to simulate JSON mode support."""
        self.supports_json_mode_called = True
        return True
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "mock"


@pytest.mark.unit
class TestIntentDetector:
    """Unit tests for IntentDetector class."""
    
    def test_initialization(self):
        """Test IntentDetector initialization."""
        mock_provider = MockLLMProvider()
        detector = IntentDetector(llm_provider=mock_provider, temperature=0.1)
        
        assert detector.llm_provider == mock_provider
        assert detector.temperature == 0.1
        assert detector.SUPPORTED_INTENTS == ['jira_creation', 'rag_query', 'general_chat', 'coze_agent']
    
    def test_detect_intent_jira_creation(self):
        """Test intent detection for Jira creation."""
        response = json.dumps({
            "intent": "jira_creation",
            "confidence": 0.9,
            "reasoning": "User wants to create a Jira ticket"
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("I need to create a Jira ticket for a bug")
        
        assert result["intent"] == "jira_creation"
        assert result["confidence"] == 0.9
        assert "reasoning" in result
        assert mock_provider.supports_json_mode_called
        assert mock_provider.generate_response_called
    
    def test_detect_intent_rag_query(self):
        """Test intent detection for RAG query."""
        response = json.dumps({
            "intent": "rag_query",
            "confidence": 0.85,
            "reasoning": "User wants documentation information"
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("What is the documentation for this feature?")
        
        assert result["intent"] == "rag_query"
        assert result["confidence"] == 0.85
    
    def test_detect_intent_general_chat(self):
        """Test intent detection for general chat."""
        response = json.dumps({
            "intent": "general_chat",
            "confidence": 0.7,
            "reasoning": "General conversation"
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Hello, how are you?")
        
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.7
    
    def test_detect_intent_with_context(self):
        """Test intent detection with conversation context."""
        response = json.dumps({
            "intent": "jira_creation",
            "confidence": 0.9,
            "reasoning": "User wants to create a Jira ticket"
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        context = [
            "User: I have a bug to report",
            "Assistant: I can help you create a Jira ticket"
        ]
        result = detector.detect_intent("Yes, please create it", conversation_context=context)
        
        assert result["intent"] == "jira_creation"
        # Verify context was included in prompt (indirectly through LLM call)
        assert mock_provider.generate_response_called
    
    def test_detect_intent_unsupported_intent(self):
        """Test that unsupported intents default to general_chat."""
        response = json.dumps({
            "intent": "unknown_intent",
            "confidence": 0.8,
            "reasoning": "Unknown intent"
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Some input")
        
        # Should default to general_chat for unsupported intent
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.5  # Lower confidence for invalid intent
    
    def test_detect_intent_invalid_confidence(self):
        """Test that invalid confidence scores are clamped."""
        response = json.dumps({
            "intent": "general_chat",
            "confidence": 1.5,  # Invalid: > 1.0
            "reasoning": "Test"
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Test input")
        
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 1.0  # Clamped to max
    
    def test_detect_intent_missing_fields(self):
        """Test handling of missing fields in LLM response."""
        response = json.dumps({
            "intent": "general_chat"
            # Missing confidence and reasoning
        })
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Test input")
        
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.7  # Default confidence
        assert "reasoning" in result
    
    def test_detect_intent_json_in_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = "```json\n" + json.dumps({
            "intent": "rag_query",
            "confidence": 0.8,
            "reasoning": "Test"
        }) + "\n```"
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Test input")
        
        assert result["intent"] == "rag_query"
        assert result["confidence"] == 0.8
    
    def test_detect_intent_json_parsing_failure(self):
        """Test fallback when JSON parsing fails."""
        response = "This is not valid JSON. The intent is jira_creation."
        mock_provider = MockLLMProvider(response=response)
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Test input")
        
        # Should extract intent from text
        assert result["intent"] == "jira_creation"
        assert result["confidence"] == 0.5  # Lower confidence for text extraction
        assert "JSON parsing failed" in result["reasoning"]
    
    def test_detect_intent_llm_error(self):
        """Test error handling when LLM call fails."""
        mock_provider = MockLLMProvider()
        mock_provider.generate_response = Mock(side_effect=Exception("LLM API error"))
        detector = IntentDetector(llm_provider=mock_provider)
        
        result = detector.detect_intent("Test input")
        
        # Should fallback to general_chat on error
        assert result["intent"] == "general_chat"
        assert result["confidence"] == 0.0
        assert "Error during detection" in result["reasoning"]
    
    def test_create_intent_prompt_with_context(self):
        """Test prompt creation with conversation context."""
        mock_provider = MockLLMProvider()
        detector = IntentDetector(llm_provider=mock_provider)
        
        context = ["User: Hello", "Assistant: Hi there"]
        prompt = detector._create_intent_prompt("What can you do?", context)
        
        assert "Recent conversation context" in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there" in prompt
        assert "Current user input" in prompt
        assert "What can you do?" in prompt
        assert "Intent descriptions" in prompt
    
    def test_create_intent_prompt_without_context(self):
        """Test prompt creation without conversation context."""
        mock_provider = MockLLMProvider()
        detector = IntentDetector(llm_provider=mock_provider)
        
        prompt = detector._create_intent_prompt("Hello", None)
        
        assert "Current user input" in prompt
        assert "Hello" in prompt
        assert "Intent descriptions" in prompt
        assert "Recent conversation context" not in prompt
    
    def test_extract_intent_from_text(self):
        """Test intent extraction from text when JSON parsing fails."""
        mock_provider = MockLLMProvider()
        detector = IntentDetector(llm_provider=mock_provider)
        
        # Test with intent in text
        intent = detector._extract_intent_from_text("The intent is jira_creation")
        assert intent == "jira_creation"
        
        # Test with no intent in text
        intent = detector._extract_intent_from_text("Some random text")
        assert intent == "general_chat"  # Default fallback
    
    def test_temperature_parameter(self):
        """Test that temperature parameter is used."""
        mock_provider = MockLLMProvider()
        detector = IntentDetector(llm_provider=mock_provider, temperature=0.5)
        
        result = detector.detect_intent("Test")
        
        # Verify temperature was passed to LLM
        assert detector.temperature == 0.5
        assert mock_provider.last_temperature == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

