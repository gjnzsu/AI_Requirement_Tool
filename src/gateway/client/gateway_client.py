"""
Gateway client library.

Internal client for making requests to the gateway.
"""

import httpx
import asyncio
from typing import List, Optional, Dict, Any
from ..config.gateway_config import GatewayConfig


class GatewayClient:
    """
    Client for making requests to the AI Gateway.
    
    Supports both async and sync operations.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        """
        Initialize gateway client.
        
        Args:
            base_url: Gateway base URL (defaults to config)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or f"http://{GatewayConfig.GATEWAY_HOST}:{GatewayConfig.GATEWAY_PORT}"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        cache: bool = True,
        routing_strategy: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Make a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            provider: Provider name
            temperature: Temperature setting
            max_tokens: Max tokens
            json_mode: JSON mode flag
            cache: Whether to use cache
            routing_strategy: Routing strategy
            user_id: User ID
            timeout: Request timeout
            
        Returns:
            Response dictionary
        """
        client = await self._get_client()
        
        payload = {
            "messages": messages,
            "cache": cache
        }
        
        if model:
            payload["model"] = model
        if provider:
            payload["provider"] = provider
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if json_mode:
            payload["json_mode"] = json_mode
        if routing_strategy:
            payload["routing_strategy"] = routing_strategy
        if user_id:
            payload["user_id"] = user_id
        if timeout:
            payload["timeout"] = timeout
        
        try:
            response = await client.post(
                "/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"Rate limit exceeded: {e.response.text}")
            raise Exception(f"Gateway error: {e.response.text}")
        except Exception as e:
            raise Exception(f"Gateway request failed: {str(e)}")
    
    def chat_completion_sync(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Synchronous version of chat_completion.
        
        Args:
            messages: List of message dicts
            **kwargs: Same as chat_completion
            
        Returns:
            Response dictionary
        """
        return asyncio.run(self.chat_completion(messages, **kwargs))
    
    async def health_check(self) -> Dict[str, Any]:
        """Check gateway health."""
        client = await self._get_client()
        try:
            response = await client.get("/v1/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Health check failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

