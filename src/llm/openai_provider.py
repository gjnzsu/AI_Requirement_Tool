"""
OpenAI LLM Provider Implementation.
"""

import os
from typing import Optional
from openai import OpenAI
from .base_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", **kwargs):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo-preview')
            **kwargs: Additional OpenAI client parameters
        """
        super().__init__(api_key, model, **kwargs)
        # Extract timeout from kwargs or use default (slightly less than INTENT_LLM_TIMEOUT)
        # This ensures API calls timeout before the ThreadPoolExecutor timeout
        timeout = kwargs.pop('timeout', None)
        if timeout is None:
            # Try to get from environment variable or use default
            try:
                from config.config import Config
                # Use 0.5s less than INTENT_LLM_TIMEOUT to ensure proper error handling
                timeout = float(os.getenv('OPENAI_API_TIMEOUT', str(Config.INTENT_LLM_TIMEOUT - 0.5)))
            except (ImportError, AttributeError):
                # Fallback if config not available
                timeout = 4.5  # Default 4.5s (less than 5s ThreadPool timeout)
        self.client = OpenAI(api_key=api_key, timeout=timeout, **kwargs)
    
    def generate_response(self, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.3, json_mode: bool = False,
                         timeout: float = None) -> str:
        """Generate response using OpenAI API.
        
        Args:
            system_prompt: System message/instructions
            user_prompt: User message/content
            temperature: Sampling temperature (0.0 to 1.0)
            json_mode: Whether to force JSON response format
            timeout: Override timeout for this request (seconds). Default uses client timeout.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        # Add JSON mode if supported
        if json_mode and self.supports_json_mode():
            params["response_format"] = {"type": "json_object"}
        
        # Use custom timeout if provided, otherwise use client default
        if timeout is not None:
            response = self.client.with_options(timeout=timeout).chat.completions.create(**params)
        else:
            response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content.strip()
    
    def supports_json_mode(self) -> bool:
        """OpenAI supports JSON mode for gpt-3.5-turbo and gpt-4 models."""
        return "gpt-3.5" in self.model.lower() or "gpt-4" in self.model.lower()
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "openai"

