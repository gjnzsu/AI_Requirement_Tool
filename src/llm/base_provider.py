"""
Abstract base class for LLM providers.

This module defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers must implement this interface to ensure compatibility
    with the Jira Maturity Evaluator service.
    """
    
    def __init__(self, api_key: str, model: str, **kwargs):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: API key for the LLM service
            model: Model name/identifier to use
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs
    
    @abstractmethod
    def generate_response(self, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.3, json_mode: bool = False,
                         timeout: float = None) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: System message/instructions
            user_prompt: User message/content
            temperature: Sampling temperature (0.0 to 1.0)
            json_mode: Whether to force JSON response format
            timeout: Override timeout for this specific request (in seconds).
                     If None, uses the provider's default timeout.
                     Use longer timeouts (e.g., 60s) for complex tasks like evaluation.
            
        Returns:
            Generated text response from the LLM
        """
        pass
    
    @abstractmethod
    def supports_json_mode(self) -> bool:
        """
        Check if this provider supports JSON mode.
        
        Returns:
            True if JSON mode is supported, False otherwise
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.
        
        Returns:
            Provider name (e.g., 'openai', 'gemini', 'deepseek')
        """
        pass

