"""
Unit tests for router.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.gateway.routing.router import Router
from src.gateway.providers.base_adapter import BaseProviderAdapter
from src.gateway.middleware.metrics import MetricsCollector
from src.gateway.routing.circuit_breaker import CircuitBreaker


class MockAdapter(BaseProviderAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, provider_name: str, model: str = "test-model"):
        from src.llm.base_provider import LLMProvider
        mock_provider = Mock(spec=LLMProvider)
        mock_provider.get_provider_name.return_value = provider_name
        mock_provider.model = model
        super().__init__(mock_provider)
    
    async def generate_completion(self, messages, **kwargs):
        return {"content": "test", "provider": self.provider_name}


class TestRouter:
    """Tests for Router."""
    
    def test_router_explicit_routing(self):
        """Test explicit routing strategy."""
        adapters = [
            MockAdapter("openai"),
            MockAdapter("gemini"),
            MockAdapter("deepseek")
        ]
        
        router = Router(strategy="explicit")
        
        # Should select explicitly requested provider
        selected = router.select_provider(adapters, explicit_provider="gemini")
        assert selected.get_provider_name() == "gemini"
    
    def test_router_cost_based_routing(self):
        """Test cost-based routing strategy."""
        adapters = [
            MockAdapter("openai"),
            MockAdapter("gemini"),
            MockAdapter("deepseek")
        ]
        
        router = Router(strategy="cost")
        
        # Should prefer cheaper providers (deepseek -> gemini -> openai)
        selected = router.select_provider(adapters)
        assert selected.get_provider_name() == "deepseek"
    
    def test_router_latency_based_routing(self):
        """Test latency-based routing strategy."""
        adapters = [
            MockAdapter("openai"),
            MockAdapter("gemini")
        ]
        
        metrics = MetricsCollector(enabled=True)
        # Set lower latency for gemini
        metrics.record_request("gemini", latency_ms=100.0, success=True)
        metrics.record_request("openai", latency_ms=200.0, success=True)
        
        router = Router(strategy="latency", metrics_collector=metrics)
        
        # Should select provider with lower latency
        selected = router.select_provider(adapters)
        assert selected.get_provider_name() == "gemini"
    
    def test_router_load_based_routing(self):
        """Test load-based routing strategy."""
        adapters = [
            MockAdapter("openai"),
            MockAdapter("gemini")
        ]
        
        metrics = MetricsCollector(enabled=True)
        # Set lower request count for gemini
        metrics.record_request("gemini", latency_ms=100.0, success=True)
        metrics.record_request("openai", latency_ms=100.0, success=True)
        metrics.record_request("openai", latency_ms=100.0, success=True)
        
        router = Router(strategy="load", metrics_collector=metrics)
        
        # Should select provider with fewer requests
        selected = router.select_provider(adapters)
        assert selected.get_provider_name() == "gemini"
    
    def test_router_circuit_breaker_filtering(self):
        """Test that router filters out unavailable providers."""
        adapters = [
            MockAdapter("openai"),
            MockAdapter("gemini")
        ]
        
        circuit_breaker = CircuitBreaker(failure_threshold=3, enabled=True)
        # Open circuit for openai (3 failures)
        circuit_breaker.record_failure("openai")
        circuit_breaker.record_failure("openai")
        circuit_breaker.record_failure("openai")
        
        router = Router(strategy="explicit", circuit_breaker=circuit_breaker)
        
        # Should select gemini (openai is unavailable)
        selected = router.select_provider(adapters)
        assert selected.get_provider_name() == "gemini"
    
    def test_router_no_available_providers(self):
        """Test that router raises error when no providers available."""
        adapters = [
            MockAdapter("openai"),
            MockAdapter("gemini")
        ]
        
        circuit_breaker = CircuitBreaker(failure_threshold=2, enabled=True)
        # Open circuits for all providers (2 failures each)
        for provider in ["openai", "gemini"]:
            circuit_breaker.record_failure(provider)
            circuit_breaker.record_failure(provider)
        
        router = Router(strategy="explicit", circuit_breaker=circuit_breaker)
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="No providers available"):
            router.select_provider(adapters)

