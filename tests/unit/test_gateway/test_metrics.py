"""
Unit tests for metrics collector.
"""

import pytest
from src.gateway.middleware.metrics import MetricsCollector


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    def test_metrics_record_request(self):
        """Test recording request metrics."""
        metrics = MetricsCollector(enabled=True)
        
        metrics.record_request(
            provider="openai",
            latency_ms=100.0,
            success=True,
            tokens=50
        )
        
        provider_metrics = metrics.get_provider_metrics("openai")
        assert provider_metrics.request_count == 1
        assert provider_metrics.success_count == 1
        assert provider_metrics.error_count == 0
        assert provider_metrics.average_latency_ms == 100.0
        assert provider_metrics.total_tokens == 50
    
    def test_metrics_record_error(self):
        """Test recording error metrics."""
        metrics = MetricsCollector(enabled=True)
        
        metrics.record_request(
            provider="openai",
            latency_ms=50.0,
            success=False
        )
        
        provider_metrics = metrics.get_provider_metrics("openai")
        assert provider_metrics.request_count == 1
        assert provider_metrics.success_count == 0
        assert provider_metrics.error_count == 1
    
    def test_metrics_cache_tracking(self):
        """Test cache hit/miss tracking."""
        metrics = MetricsCollector(enabled=True)
        
        # Record cache hit
        metrics.record_request(
            provider="openai",
            latency_ms=10.0,
            success=True,
            cached=True
        )
        
        # Record cache miss
        metrics.record_request(
            provider="openai",
            latency_ms=100.0,
            success=True,
            cached=False
        )
        
        assert metrics.get_cache_hit_rate() == 0.5
    
    def test_metrics_average_latency(self):
        """Test average latency calculation."""
        metrics = MetricsCollector(enabled=True)
        
        metrics.record_request("openai", latency_ms=100.0, success=True)
        metrics.record_request("openai", latency_ms=200.0, success=True)
        metrics.record_request("openai", latency_ms=300.0, success=True)
        
        provider_metrics = metrics.get_provider_metrics("openai")
        assert provider_metrics.average_latency_ms == 200.0
    
    def test_metrics_get_summary(self):
        """Test getting summary metrics."""
        metrics = MetricsCollector(enabled=True)
        
        metrics.record_request("openai", latency_ms=100.0, success=True, cached=True)
        metrics.record_request("gemini", latency_ms=150.0, success=False, cached=False)
        
        summary = metrics.get_summary()
        assert summary['total_requests'] == 2
        assert summary['total_errors'] == 1
        assert summary['cache_hit_rate'] == 0.5
        assert len(summary['provider_metrics']) == 2
    
    def test_metrics_reset(self):
        """Test resetting metrics."""
        metrics = MetricsCollector(enabled=True)
        
        metrics.record_request("openai", latency_ms=100.0, success=True)
        
        metrics.reset()
        
        provider_metrics = metrics.get_provider_metrics("openai")
        assert provider_metrics.request_count == 0
        assert metrics.get_summary()['total_requests'] == 0
    
    def test_metrics_disabled(self):
        """Test that disabled metrics don't record."""
        metrics = MetricsCollector(enabled=False)
        
        metrics.record_request("openai", latency_ms=100.0, success=True)
        
        provider_metrics = metrics.get_provider_metrics("openai")
        assert provider_metrics.request_count == 0

