"""
Metrics collector middleware.

Collects metrics about gateway requests and provider performance.
"""

import time
from typing import Dict, List, Optional, Any
from collections import defaultdict
from threading import Lock
from ..models.response_models import ProviderMetrics


class MetricsCollector:
    """
    Metrics collector for gateway operations.
    
    Tracks request counts, latencies, errors, and token usage per provider.
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize metrics collector.
        
        Args:
            enabled: Whether metrics collection is enabled
        """
        self.enabled = enabled
        
        # Metrics storage
        self._request_counts: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._token_counts: Dict[str, int] = defaultdict(int)
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_requests = 0
        self._total_errors = 0
        self._lock = Lock()
    
    def record_request(
        self,
        provider: str,
        latency_ms: float,
        success: bool,
        tokens: int = 0,
        cached: bool = False
    ):
        """
        Record a request metric.
        
        Args:
            provider: Provider name
            latency_ms: Request latency in milliseconds
            success: Whether request was successful
            tokens: Number of tokens processed
            cached: Whether response was from cache
        """
        if not self.enabled:
            return
        
        with self._lock:
            self._request_counts[provider] += 1
            self._total_requests += 1
            
            if cached:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
            
            if success:
                self._success_counts[provider] += 1
            else:
                self._error_counts[provider] += 1
                self._total_errors += 1
            
            # Store latency (keep last 1000 for each provider)
            self._latencies[provider].append(latency_ms)
            if len(self._latencies[provider]) > 1000:
                self._latencies[provider].pop(0)
            
            if tokens > 0:
                self._token_counts[provider] += tokens
    
    def get_provider_metrics(self, provider: str) -> ProviderMetrics:
        """
        Get metrics for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            ProviderMetrics object
        """
        with self._lock:
            latencies = self._latencies.get(provider, [])
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            
            return ProviderMetrics(
                provider=provider,
                request_count=self._request_counts.get(provider, 0),
                success_count=self._success_counts.get(provider, 0),
                error_count=self._error_counts.get(provider, 0),
                average_latency_ms=avg_latency,
                total_tokens=self._token_counts.get(provider, 0)
            )
    
    def get_all_provider_metrics(self) -> List[ProviderMetrics]:
        """
        Get metrics for all providers.
        
        Returns:
            List of ProviderMetrics objects
        """
        with self._lock:
            providers = set(self._request_counts.keys())
            result = []
            for provider in providers:
                latencies = self._latencies.get(provider, [])
                avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
                result.append(
                    ProviderMetrics(
                        provider=provider,
                        request_count=self._request_counts.get(provider, 0),
                        success_count=self._success_counts.get(provider, 0),
                        error_count=self._error_counts.get(provider, 0),
                        average_latency_ms=avg_latency,
                        total_tokens=self._token_counts.get(provider, 0)
                    )
                )
            return result
    
    def get_cache_hit_rate(self) -> float:
        """
        Get cache hit rate.
        
        Returns:
            Cache hit rate (0.0 to 1.0)
        """
        with self._lock:
            total = self._cache_hits + self._cache_misses
            if total == 0:
                return 0.0
            return self._cache_hits / total
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary metrics.
        
        Returns:
            Dictionary with summary metrics
        """
        with self._lock:
            total = self._cache_hits + self._cache_misses
            cache_hit_rate = self._cache_hits / total if total > 0 else 0.0
            provider_metrics = []
            for provider in set(self._request_counts.keys()):
                latencies = self._latencies.get(provider, [])
                avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
                pm = ProviderMetrics(
                    provider=provider,
                    request_count=self._request_counts.get(provider, 0),
                    success_count=self._success_counts.get(provider, 0),
                    error_count=self._error_counts.get(provider, 0),
                    average_latency_ms=avg_latency,
                    total_tokens=self._token_counts.get(provider, 0)
                )
                provider_metrics.append(pm.model_dump() if hasattr(pm, 'model_dump') else pm.dict())
            return {
                'total_requests': self._total_requests,
                'total_errors': self._total_errors,
                'cache_hit_rate': cache_hit_rate,
                'provider_metrics': provider_metrics
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._request_counts.clear()
            self._success_counts.clear()
            self._error_counts.clear()
            self._latencies.clear()
            self._token_counts.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._total_requests = 0
            self._total_errors = 0

