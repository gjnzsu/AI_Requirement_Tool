"""
Intent Detection Service

This service uses LLM to detect user intent when keyword-based detection
is ambiguous or fails to match.
"""

import json
import re
from typing import List, Dict, Optional, Any
from src.llm import LLMProvider
from src.utils.logger import get_logger

logger = get_logger('chatbot.services.intent_detector')


class IntentDetector:
    """
    Service to detect user intent using LLM-based classification.
    
    Provides structured intent detection with confidence scores,
    supporting conversation context for better accuracy.
    """
    
    # Supported intent types
    SUPPORTED_INTENTS = ['jira_creation', 'rag_query', 'general_chat', 'coze_agent']
    
    def __init__(self, llm_provider: LLMProvider, temperature: float = 0.1):
        """
        Initialize the Intent Detector.
        
        Args:
            llm_provider: LLM provider instance (from LLMRouter)
            temperature: Sampling temperature for LLM (default: 0.1 for deterministic)
        """
        self.llm_provider = llm_provider
        self.temperature = temperature
        
    def detect_intent(self, user_input: str, conversation_context: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Detect user intent from input using LLM.
        
        Args:
            user_input: User's input message
            conversation_context: Optional list of recent conversation messages for context
            
        Returns:
            Dictionary with:
                - intent: str - Detected intent ('jira_creation', 'rag_query', 'general_chat', 'coze_agent')
                - confidence: float - Confidence score (0.0 to 1.0)
                - reasoning: str - Brief explanation of the detection
        """
        try:
            # Create prompt for intent detection
            prompt = self._create_intent_prompt(user_input, conversation_context)
            
            # System prompt for intent classification
            system_prompt = (
                "You are an expert intent classifier for a chatbot system. "
                "Analyze the user's input and determine their intent. "
                "Return a JSON response with 'intent', 'confidence' (0.0-1.0), and 'reasoning' fields. "
                "Available intents: jira_creation, rag_query, general_chat, coze_agent. "
                "Be precise and confident in your classification."
            )
            
            # Use JSON mode if supported by the provider
            json_mode = self.llm_provider.supports_json_mode()
            
            # Call LLM provider for intent detection
            response_content = self.llm_provider.generate_response(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=self.temperature,
                json_mode=json_mode
            )
            
            # Parse LLM response
            result = self._parse_llm_response(response_content)
            
            # Validate intent
            if result['intent'] not in self.SUPPORTED_INTENTS:
                logger.warning(f"LLM returned unsupported intent: {result['intent']}, defaulting to general_chat")
                result['intent'] = 'general_chat'
                result['confidence'] = 0.5
            
            # Validate confidence score
            if not (0.0 <= result['confidence'] <= 1.0):
                logger.warning(f"Invalid confidence score: {result['confidence']}, clamping to [0.0, 1.0]")
                result['confidence'] = max(0.0, min(1.0, result['confidence']))
            
            logger.debug(f"Intent detected: {result['intent']} (confidence: {result['confidence']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM intent detection: {e}")
            # Fallback to general_chat on error
            return {
                'intent': 'general_chat',
                'confidence': 0.0,
                'reasoning': f'Error during detection: {str(e)}'
            }
    
    def _create_intent_prompt(self, user_input: str, context: Optional[List[str]]) -> str:
        """
        Create prompt for intent detection.
        
        Args:
            user_input: User's input message
            context: Optional conversation context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Add conversation context if available
        if context and len(context) > 0:
            prompt_parts.append("Recent conversation context:")
            for i, msg in enumerate(context[-3:], 1):  # Last 3 messages for context
                prompt_parts.append(f"{i}. {msg}")
            prompt_parts.append("")
        
        # Add current user input
        prompt_parts.append("Current user input:")
        prompt_parts.append(user_input)
        prompt_parts.append("")
        
        # Add intent descriptions
        prompt_parts.append("Intent descriptions:")
        prompt_parts.append("- jira_creation: User wants to create a Jira issue/ticket/backlog item")
        prompt_parts.append("- rag_query: User wants to search documentation or get information from knowledge base")
        prompt_parts.append("- general_chat: General conversation, greetings, or questions not requiring specific tools")
        prompt_parts.append("- coze_agent: User wants AI daily report or AI news (if Coze is enabled)")
        prompt_parts.append("")
        prompt_parts.append("Analyze the user input and determine the most appropriate intent.")
        
        return "\n".join(prompt_parts)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract intent, confidence, and reasoning.
        
        Args:
            response: Raw LLM response string
            
        Returns:
            Dictionary with intent, confidence, and reasoning
        """
        # Try to extract JSON if response_format wasn't used
        cleaned_response = response.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```'):
            lines = cleaned_response.split('\n')
            json_lines = [line for line in lines if not line.strip().startswith('```')]
            cleaned_response = '\n'.join(json_lines)
        
        # Try to find JSON object in response
        if not cleaned_response.startswith('{'):
            start_idx = cleaned_response.find('{')
            end_idx = cleaned_response.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                cleaned_response = cleaned_response[start_idx:end_idx]
        
        try:
            result = json.loads(cleaned_response)
            
            # Ensure required fields exist
            if 'intent' not in result:
                raise ValueError("Missing 'intent' field in LLM response")
            
            # Set defaults for optional fields
            if 'confidence' not in result:
                result['confidence'] = 0.7  # Default confidence
            if 'reasoning' not in result:
                result['reasoning'] = 'Intent detected based on user input analysis'
            
            return {
                'intent': result['intent'].lower(),
                'confidence': float(result['confidence']),
                'reasoning': str(result.get('reasoning', ''))
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Raw response: {response[:200]}")
            
            # Try to extract intent from text if JSON parsing fails
            intent = self._extract_intent_from_text(response)
            return {
                'intent': intent,
                'confidence': 0.5,  # Lower confidence for text-based extraction
                'reasoning': 'Intent extracted from text response (JSON parsing failed)'
            }
    
    def _extract_intent_from_text(self, text: str) -> str:
        """
        Extract intent from text response when JSON parsing fails.
        
        Args:
            text: Text response from LLM
            
        Returns:
            Detected intent string
        """
        text_lower = text.lower()
        
        # Look for intent mentions in text
        for intent in self.SUPPORTED_INTENTS:
            if intent in text_lower:
                return intent
        
        # Default to general_chat if no intent found
        return 'general_chat'

