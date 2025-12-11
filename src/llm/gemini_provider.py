"""
Google Gemini LLM Provider Implementation.
"""

import os
from typing import Optional
try:
    import google.generativeai as genai
except ImportError:
    genai = None
from .base_provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-pro", 
                 proxy: Optional[str] = None, **kwargs):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            model: Model name (e.g., 'gemini-pro', 'gemini-1.5-pro', 'gemini-1.5-flash')
            proxy: Proxy URL (e.g., 'http://proxy.example.com:8080' or 'socks5://proxy.example.com:1080')
            **kwargs: Additional Gemini client parameters
        """
        if genai is None:
            raise ImportError(
                "google-generativeai package is required for Gemini provider. "
                "Install it with: pip install google-generativeai"
            )
        super().__init__(api_key, model, **kwargs)
        
        # Configure proxy if provided
        if proxy:
            # Set proxy environment variables for the google-generativeai library
            # The library uses requests/urllib3 which respects HTTP_PROXY and HTTPS_PROXY
            os.environ['HTTP_PROXY'] = proxy
            os.environ['HTTPS_PROXY'] = proxy
            print(f"Gemini provider configured with proxy: {proxy}")
        
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name=model)
        self.proxy = proxy
    
    def generate_response(self, system_prompt: str, user_prompt: str, 
                         temperature: float = 0.3, json_mode: bool = False) -> str:
        """Generate response using Gemini API."""
        # Combine system and user prompts for Gemini
        # Gemini doesn't have separate system/user roles in the same way
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Add JSON instruction if needed
        if json_mode:
            full_prompt += "\n\nPlease respond with valid JSON only, no additional text."
        
        generation_config = {
            "temperature": temperature,
        }
        
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
        
        try:
            response = self.client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(**generation_config)
            )
            
            return response.text.strip()
        except Exception as e:
            # Check for rate limit errors (HTTP 429)
            error_str = str(e).lower()
            error_type = type(e).__name__
            
            # Check if it's a rate limit error
            if '429' in error_str or 'rate limit' in error_str or 'quota' in error_str:
                # Create a custom exception with status_code attribute for better error handling
                class RateLimitError(Exception):
                    def __init__(self, message):
                        super().__init__(message)
                        self.status_code = 429
                        self.error_type = 'RateLimitError'
                
                raise RateLimitError(
                    f"Gemini API rate limit exceeded: {str(e)}. "
                    f"Please wait a few minutes before trying again."
                )
            
            # Re-raise other exceptions as-is
            raise
    
    def supports_json_mode(self) -> bool:
        """Gemini supports JSON mode via response_mime_type."""
        return True
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "gemini"

