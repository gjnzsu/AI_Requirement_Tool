"""
Unit tests for rate limiter.
"""

import pytest
import time
from src.gateway.middleware.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_rate_limiter_allows_requests_when_enabled(self):
        """Test that rate limiter allows requests within limits."""
        limiter = RateLimiter(
            requests_per_minute=10,
            requests_per_hour=100,
            enabled=True
        )
        
        # First 10 requests should be allowed
        for i in range(10):
            allowed, retry_after = limiter.check_rate_limit(identifier="test")
            assert allowed is True
            assert retry_after is None
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that rate limiter blocks requests over limit."""
        limiter = RateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
            enabled=True
        )
        
        # First 5 requests should be allowed
        for i in range(5):
            allowed, _ = limiter.check_rate_limit(identifier="test")
            assert allowed is True
        
        # 6th request should be blocked
        allowed, retry_after = limiter.check_rate_limit(identifier="test")
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_rate_limiter_disabled_allows_all(self):
        """Test that disabled rate limiter allows all requests."""
        limiter = RateLimiter(enabled=False)
        
        # Should allow unlimited requests
        for i in range(100):
            allowed, retry_after = limiter.check_rate_limit(identifier="test")
            assert allowed is True
            assert retry_after is None
    
    def test_rate_limiter_per_user_limits(self):
        """Test that rate limiter enforces per-user limits."""
        limiter = RateLimiter(
            requests_per_minute=5,
            requests_per_hour=100,
            enabled=True
        )
        
        # User 1 should be able to make 5 requests
        for i in range(5):
            allowed, _ = limiter.check_rate_limit(user_id="user1")
            assert allowed is True
        
        # User 2 should also be able to make 5 requests
        for i in range(5):
            allowed, _ = limiter.check_rate_limit(user_id="user2")
            assert allowed is True
        
        # Both users should now be blocked
        allowed1, _ = limiter.check_rate_limit(user_id="user1")
        allowed2, _ = limiter.check_rate_limit(user_id="user2")
        assert allowed1 is False
        assert allowed2 is False
    
    def test_rate_limiter_reset(self):
        """Test that rate limiter reset clears limits."""
        limiter = RateLimiter(
            requests_per_minute=5,
            enabled=True
        )
        
        # Exhaust limit
        for i in range(5):
            limiter.check_rate_limit(identifier="test")
        
        # Should be blocked
        allowed, _ = limiter.check_rate_limit(identifier="test")
        assert allowed is False
        
        # Reset
        limiter.reset(identifier="test")
        
        # Should be allowed again
        allowed, _ = limiter.check_rate_limit(identifier="test")
        assert allowed is True

