"""
Unit tests for fallback manager.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.gateway.routing.fallback import FallbackManager
from src.gateway.providers.base_adapter import BaseProviderAdapter
from src.gateway.routing.circuit_breaker import CircuitBreaker


class MockAdapter(BaseProviderAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, provider_name: str, should_fail: bool = False):
        from src.llm.base_provider import LLMProvider
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.get_provider_name.return_value = provider_name
        mock_provider.model = "test-model"
        super().__init__(mock_provider)
        self.should_fail = should_fail
    
    async def generate_completion(self, messages, **kwargs):
        if self.should_fail:
            raise Exception(f"{self.provider_name} failed")
        return {"content": f"response from {self.provider_name}", "provider": self.provider_name}


class TestFallbackManager:
    """Tests for FallbackManager."""
    
    @pytest.mark.asyncio
    async def test_fallback_success_on_primary(self):
        """Test that fallback succeeds on primary provider."""
        primary = MockAdapter("openai", should_fail=False)
        fallback = MockAdapter("gemini", should_fail=False)
        
        manager = FallbackManager(enabled=True)
        
        result = await manager.execute_with_fallback(
            primary_adapter=primary,
            fallback_adapters=[fallback],
            messages=[{"role": "user", "content": "test"}]
        )
        
        assert result["provider"] == "openai"
        assert "response from openai" in result["content"]
    
    @pytest.mark.asyncio
    async def test_fallback_uses_fallback_on_primary_failure(self):
        """Test that fallback uses fallback provider when primary fails."""
        primary = MockAdapter("openai", should_fail=True)
        fallback = MockAdapter("gemini", should_fail=False)
        
        manager = FallbackManager(enabled=True)
        
        result = await manager.execute_with_fallback(
            primary_adapter=primary,
            fallback_adapters=[fallback],
            messages=[{"role": "user", "content": "test"}]
        )
        
        assert result["provider"] == "gemini"
        assert "response from gemini" in result["content"]
    
    @pytest.mark.asyncio
    async def test_fallback_fails_when_all_providers_fail(self):
        """Test that fallback raises error when all providers fail."""
        primary = MockAdapter("openai", should_fail=True)
        fallback = MockAdapter("gemini", should_fail=True)
        
        manager = FallbackManager(enabled=True)
        
        with pytest.raises(Exception, match="All providers failed"):
            await manager.execute_with_fallback(
                primary_adapter=primary,
                fallback_adapters=[fallback],
                messages=[{"role": "user", "content": "test"}]
            )
    
    @pytest.mark.asyncio
    async def test_fallback_respects_circuit_breaker(self):
        """Test that fallback respects circuit breaker."""
        primary = MockAdapter("openai", should_fail=False)
        fallback = MockAdapter("gemini", should_fail=False)
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            enabled=True
        )
        # Open circuit for primary (3 failures)
        circuit_breaker.record_failure("openai")
        circuit_breaker.record_failure("openai")
        circuit_breaker.record_failure("openai")
        
        manager = FallbackManager(enabled=True, circuit_breaker=circuit_breaker)
        
        # Should skip primary and use fallback
        result = await manager.execute_with_fallback(
            primary_adapter=primary,
            fallback_adapters=[fallback],
            messages=[{"role": "user", "content": "test"}]
        )
        
        assert result["provider"] == "gemini"
    
    @pytest.mark.asyncio
    async def test_fallback_disabled_uses_primary_only(self):
        """Test that disabled fallback only uses primary."""
        primary = MockAdapter("openai", should_fail=False)
        fallback = MockAdapter("gemini", should_fail=False)
        
        manager = FallbackManager(enabled=False)
        
        result = await manager.execute_with_fallback(
            primary_adapter=primary,
            fallback_adapters=[fallback],
            messages=[{"role": "user", "content": "test"}]
        )
        
        assert result["provider"] == "openai"

