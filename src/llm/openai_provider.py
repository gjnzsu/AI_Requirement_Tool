"""
OpenAI LLM Provider Implementation.
"""

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
        self.client = OpenAI(api_key=api_key, **kwargs)
    
    def generate_response(self, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.3, json_mode: bool = False) -> str:
        """Generate response using OpenAI API."""
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
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content.strip()
    
    def supports_json_mode(self) -> bool:
        """OpenAI supports JSON mode for gpt-3.5-turbo and gpt-4 models."""
        return "gpt-3.5" in self.model.lower() or "gpt-4" in self.model.lower()
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "openai"

