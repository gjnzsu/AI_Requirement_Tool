"""
Integration tests for gateway full flow.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.gateway.gateway_service import GatewayService
from src.gateway.models.request_models import ChatCompletionRequest, ChatMessage


class TestGatewayIntegration:
    """Tests for gateway integration flow."""
    
    @pytest.fixture
    def gateway(self):
        """Create gateway service instance."""
        # Mock the provider initialization to avoid requiring real API keys
        with patch('src.gateway.gateway_service.AdapterFactory.create_adapter') as mock_factory:
            mock_adapter = Mock()
            mock_adapter.get_provider_name.return_value = "openai"
            mock_adapter.get_model.return_value = "gpt-3.5-turbo"
            # generate_completion must be async (awaitable)
            mock_adapter.generate_completion = AsyncMock(return_value={
                "content": "Test response",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "model": "gpt-3.5-turbo",
                "provider": "openai"
            })
            mock_factory.return_value = mock_adapter
            
            gateway = GatewayService()
            gateway._adapters = [mock_adapter]
            return gateway
    
    @pytest.mark.asyncio
    async def test_gateway_chat_completion_flow(self, gateway):
        """Test full chat completion flow."""
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="user", content="Hello, world!")
            ],
            temperature=0.7
        )
        
        response = await gateway.chat_completion(request)
        
        assert response.id is not None
        assert response.model is not None
        assert len(response.choices) > 0
        assert response.choices[0].message["content"] == "Test response"
    
    @pytest.mark.asyncio
    async def test_gateway_rate_limiting(self, gateway):
        """Test that rate limiting works."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            user_id="test_user"
        )
        
        # Exhaust rate limit
        gateway.rate_limiter.requests_per_minute = 2
        
        # First two requests should succeed
        response1 = await gateway.chat_completion(request)
        assert response1 is not None
        
        response2 = await gateway.chat_completion(request)
        assert response2 is not None
        
        # Third request should be rate limited
        with pytest.raises(Exception):  # Should raise HTTPException
            await gateway.chat_completion(request)
    
    @pytest.mark.asyncio
    async def test_gateway_caching(self, gateway):
        """Test that caching works."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Cached test")],
            cache=True
        )
        
        # First request should not be cached
        response1 = await gateway.chat_completion(request)
        assert response1.cached is False
        
        # Second request with same content should be cached
        response2 = await gateway.chat_completion(request)
        assert response2.cached is True
    
    def test_gateway_health_check(self, gateway):
        """Test gateway health check."""
        health = gateway.get_health()
        
        assert health.status == "healthy"
        assert isinstance(health.providers, list)
        assert isinstance(health.features, dict)
    
    def test_gateway_providers_list(self, gateway):
        """Test gateway providers list."""
        providers = gateway.get_providers()
        
        assert isinstance(providers.providers, list)
        if len(providers.providers) > 0:
            provider = providers.providers[0]
            assert "name" in provider
            assert "model" in provider
            assert "available" in provider

