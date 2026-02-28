"""
Router implementation.

Intelligent routing to select the best provider for each request.
"""

from typing import List, Optional, Literal
from ..providers.base_adapter import BaseProviderAdapter
from ..middleware.metrics import MetricsCollector
from .circuit_breaker import CircuitBreaker


class Router:
    """
    Router for selecting providers based on various strategies.
    """
    
    def __init__(
        self,
        strategy: Literal['auto', 'cost', 'latency', 'load', 'explicit'] = 'auto',
        metrics_collector: Optional[MetricsCollector] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize router.
        
        Args:
            strategy: Routing strategy
            metrics_collector: Metrics collector for latency-based routing
            circuit_breaker: Circuit breaker for health checks
        """
        self.strategy = strategy
        self.metrics_collector = metrics_collector
        self.circuit_breaker = circuit_breaker
    
    def select_provider(
        self,
        adapters: List[BaseProviderAdapter],
        explicit_provider: Optional[str] = None,
        routing_strategy: Optional[Literal['auto', 'cost', 'latency', 'load', 'explicit']] = None
    ) -> BaseProviderAdapter:
        """
        Select a provider adapter based on routing strategy.
        
        Args:
            adapters: List of available adapters
            explicit_provider: Explicitly requested provider name
            routing_strategy: Override strategy for this request
            
        Returns:
            Selected adapter
            
        Raises:
            ValueError: If no adapter is available
        """
        strategy = routing_strategy or self.strategy
        
        # Filter out unavailable providers (circuit breaker)
        available_adapters = [
            adapter for adapter in adapters
            if not self.circuit_breaker or self.circuit_breaker.is_available(adapter.get_provider_name())
        ]
        
        if not available_adapters:
            raise ValueError("No providers available (all circuits open)")
        
        # Explicit routing
        if strategy == 'explicit' or explicit_provider:
            provider_name = explicit_provider or adapters[0].get_provider_name()
            for adapter in available_adapters:
                if adapter.get_provider_name() == provider_name:
                    return adapter
            # Fallback to first available if explicit not found
            return available_adapters[0]
        
        # Cost-based routing (simple: prefer cheaper providers)
        if strategy == 'cost':
            # Order: deepseek (cheapest) -> gemini -> openai (most expensive)
            cost_order = ['deepseek', 'gemini', 'openai']
            for provider_name in cost_order:
                for adapter in available_adapters:
                    if adapter.get_provider_name() == provider_name:
                        return adapter
            return available_adapters[0]
        
        # Latency-based routing
        if strategy == 'latency' and self.metrics_collector:
            # Select provider with lowest average latency
            best_adapter = None
            best_latency = float('inf')
            
            for adapter in available_adapters:
                metrics = self.metrics_collector.get_provider_metrics(adapter.get_provider_name())
                if metrics.average_latency_ms < best_latency and metrics.request_count > 0:
                    best_latency = metrics.average_latency_ms
                    best_adapter = adapter
            
            if best_adapter:
                return best_adapter
            return available_adapters[0]
        
        # Load-based routing (select provider with fewest requests)
        if strategy == 'load' and self.metrics_collector:
            best_adapter = None
            min_requests = float('inf')
            
            for adapter in available_adapters:
                metrics = self.metrics_collector.get_provider_metrics(adapter.get_provider_name())
                if metrics.request_count < min_requests:
                    min_requests = metrics.request_count
                    best_adapter = adapter
            
            if best_adapter:
                return best_adapter
            return available_adapters[0]
        
        # Auto routing: try latency first, fallback to cost
        if strategy == 'auto':
            if self.metrics_collector:
                # Use latency-based if we have metrics
                try:
                    return self.select_provider(adapters, routing_strategy='latency')
                except:
                    pass
            # Fallback to cost-based
            return self.select_provider(adapters, routing_strategy='cost')
        
        # Default: return first available
        return available_adapters[0]

