"""
Base provider adapter.

Abstract base class for provider adapters that wrap LLMProvider instances.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import time
from src.llm.base_provider import LLMProvider


class BaseProviderAdapter(ABC):
    """
    Base adapter for LLM providers.
    
    Adapters wrap existing LLMProvider instances to add gateway-specific
    features like timeout handling, retry logic, and error normalization.
    """
    
    def __init__(self, provider: LLMProvider):
        """
        Initialize the adapter.
        
        Args:
            provider: The underlying LLMProvider instance
        """
        self.provider = provider
        self.provider_name = provider.get_provider_name()
        self.model = provider.model
    
    @abstractmethod
    async def generate_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate a completion using the provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Whether to force JSON response
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with 'content', 'usage', and other metadata
            
        Raises:
            Exception: If generation fails
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return self.provider_name
    
    def get_model(self) -> str:
        """Get the model name."""
        return self.model
    
    def supports_json_mode(self) -> bool:
        """Check if provider supports JSON mode."""
        return self.provider.supports_json_mode()
    
    def _extract_system_prompt(self, messages: list) -> Tuple[str, str]:
        """
        Extract system prompt from messages.
        
        Args:
            messages: List of message dicts
            
        Returns:
            Tuple of (system_prompt, user_messages)
        """
        system_prompt = ""
        user_messages = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                if system_prompt:
                    system_prompt += "\n" + content
                else:
                    system_prompt = content
            else:
                user_messages.append(msg)
        
        # Combine user messages into a single prompt
        user_prompt = "\n".join([
            f"{msg.get('role', 'user').title()}: {msg.get('content', '')}"
            for msg in user_messages
        ])
        
        return system_prompt or "You are a helpful assistant.", user_prompt
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation).
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4

