"""
Gateway client library.

Internal client for making requests to the gateway.
"""

import httpx
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
        timeout: float = 60.0,
        consumer_service: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        sync_http_client: Optional[httpx.Client] = None,
    ):
        """
        Initialize gateway client.
        
        Args:
            base_url: Gateway base URL (defaults to config)
            timeout: Request timeout in seconds
        """
        self.base_url = (
            base_url
            or GatewayConfig.GATEWAY_BASE_URL
            or f"http://{GatewayConfig.GATEWAY_HOST}:{GatewayConfig.GATEWAY_PORT}"
        ).rstrip("/")
        self.timeout = timeout
        self.consumer_service = consumer_service or GatewayConfig.GATEWAY_CONSUMER_SERVICE
        self._client: Optional[httpx.AsyncClient] = http_client
        self._sync_client: Optional[httpx.Client] = sync_http_client
        self._owns_async_client = http_client is None
        self._owns_sync_client = sync_http_client is None

    def _headers(self) -> Dict[str, str]:
        return {"X-Consumer-Service": self.consumer_service}

    def _chat_path(self) -> str:
        return (
            "chat/completions"
            if self.base_url.endswith("/v1")
            else "v1/chat/completions"
        )

    def _health_url(self) -> str:
        if self.base_url.endswith("/v1"):
            return f"{self.base_url[:-3]}/health"
        return f"{self.base_url}/health"

    @staticmethod
    def _should_send_provider(provider: Optional[str]) -> bool:
        return bool(provider and provider.lower() != "openai")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers(),
            )
        return self._client

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers(),
            )
        return self._sync_client
    
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
        
        payload = {"messages": messages}
        
        if model:
            payload["model"] = model
        if self._should_send_provider(provider):
            payload["provider"] = provider
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if timeout:
            payload["timeout"] = timeout
        
        try:
            response = await client.post(
                self._chat_path(),
                json=payload,
                headers=self._headers(),
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
        payload = {"messages": messages}
        model = kwargs.get("model")
        provider = kwargs.get("provider")
        temperature = kwargs.get("temperature")
        max_tokens = kwargs.get("max_tokens")
        json_mode = kwargs.get("json_mode", False)
        timeout = kwargs.get("timeout")

        if model:
            payload["model"] = model
        if self._should_send_provider(provider):
            payload["provider"] = provider
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if timeout:
            payload["timeout"] = timeout

        client = self._get_sync_client()
        try:
            response = client.post(
                self._chat_path(),
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise Exception(f"Rate limit exceeded: {e.response.text}")
            raise Exception(f"Gateway error: {e.response.text}")
        except Exception as e:
            raise Exception(f"Gateway request failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check gateway health."""
        client = await self._get_client()
        try:
            response = await client.get(self._health_url())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Health check failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and self._owns_async_client:
            await self._client.aclose()
            self._client = None
        if self._sync_client and self._owns_sync_client:
            self._sync_client.close()
            self._sync_client = None

