"""
DeepSeek LLM Provider Implementation.
"""

from typing import Optional
from openai import OpenAI
from .base_provider import LLMProvider


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider implementation (uses OpenAI-compatible API)."""
    
    def __init__(self, api_key: str, model: str = "deepseek-chat", 
                 base_url: str = "https://api.deepseek.com", **kwargs):
        """
        Initialize DeepSeek provider.
        
        Args:
            api_key: DeepSeek API key
            model: Model name (e.g., 'deepseek-chat', 'deepseek-coder')
            base_url: API base URL (default: DeepSeek API)
            **kwargs: Additional client parameters
        """
        super().__init__(api_key, model, **kwargs)
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url, **kwargs)
    
    def generate_response(self, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.3, json_mode: bool = False) -> str:
        """Generate response using DeepSeek API (OpenAI-compatible)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        # DeepSeek supports JSON mode similar to OpenAI
        if json_mode and self.supports_json_mode():
            params["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content.strip()
    
    def supports_json_mode(self) -> bool:
        """DeepSeek supports JSON mode."""
        return True
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "deepseek"

