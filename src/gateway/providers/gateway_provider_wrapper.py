"""
Gateway provider wrapper.

Wrapper that makes the gateway look like an LLMProvider for drop-in replacement.
"""

from typing import Optional
from src.llm.base_provider import LLMProvider
from ..client.gateway_client import GatewayClient


class GatewayProviderWrapper(LLMProvider):
    """
    Wrapper that makes the gateway look like an LLMProvider.
    
    This allows the gateway to be used as a drop-in replacement
    for existing LLMProvider instances.
    """
    
    def __init__(
        self,
        gateway_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ):
        """
        Initialize gateway provider wrapper.
        
        Args:
            gateway_url: Gateway URL (defaults to config)
            model: Model name (optional)
            provider: Provider name (optional)
        """
        # LLMProvider requires api_key, but gateway doesn't need it
        super().__init__(api_key="gateway", model=model or "gateway")
        self.gateway_client = GatewayClient(base_url=gateway_url)
        self.provider = provider
    
    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> str:
        """
        Generate response using gateway.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Temperature setting
            json_mode: JSON mode flag
            timeout: Request timeout
            
        Returns:
            Generated text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.gateway_client.chat_completion_sync(
                messages=messages,
                model=self.model if self.model != "gateway" else None,
                provider=self.provider,
                temperature=temperature,
                json_mode=json_mode,
                timeout=timeout
            )
            
            # Extract content from response
            if isinstance(response, dict):
                choices = response.get('choices', [])
                if choices and len(choices) > 0:
                    message = choices[0].get('message', {})
                    return message.get('content', '')
            
            return str(response)
        except Exception as e:
            raise Exception(f"Gateway error: {str(e)}") from e
    
    def supports_json_mode(self) -> bool:
        """Gateway supports JSON mode through providers."""
        return True
    
    def get_provider_name(self) -> str:
        """Return provider name."""
        return "gateway"

