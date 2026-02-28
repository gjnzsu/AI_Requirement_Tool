"""
Rate limiter middleware.

Implements token-based rate limiting for gateway requests.
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    Rate limiter for gateway requests.
    
    Supports per-user and per-API-key rate limiting.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        enabled: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
            requests_per_hour: Maximum requests per hour
            enabled: Whether rate limiting is enabled
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.enabled = enabled
        
        # Track requests: {identifier: [(timestamp, ...), ...]}
        self._minute_requests: Dict[str, list] = defaultdict(list)
        self._hour_requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()
    
    def check_rate_limit(
        self,
        identifier: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.
        
        Args:
            identifier: Rate limit identifier (API key, IP, etc.)
            user_id: User ID for per-user rate limiting
            
        Returns:
            Tuple of (allowed, retry_after_seconds)
            - allowed: True if request is allowed
            - retry_after_seconds: Seconds to wait before retry (if not allowed)
        """
        if not self.enabled:
            return True, None
        
        # Use user_id if provided, otherwise use identifier
        key = user_id or identifier or 'default'
        
        current_time = time.time()
        
        with self._lock:
            # Clean old entries
            self._clean_old_entries(key, current_time)
            
            # Check minute limit
            minute_count = len(self._minute_requests[key])
            if minute_count >= self.requests_per_minute:
                # Calculate retry after
                oldest_minute = min(self._minute_requests[key]) if self._minute_requests[key] else current_time
                retry_after = int(60 - (current_time - oldest_minute)) + 1
                return False, retry_after
            
            # Check hour limit
            hour_count = len(self._hour_requests[key])
            if hour_count >= self.requests_per_hour:
                # Calculate retry after
                oldest_hour = min(self._hour_requests[key]) if self._hour_requests[key] else current_time
                retry_after = int(3600 - (current_time - oldest_hour)) + 1
                return False, retry_after
            
            # Record request
            self._minute_requests[key].append(current_time)
            self._hour_requests[key].append(current_time)
            
            return True, None
    
    def _clean_old_entries(self, key: str, current_time: float):
        """Clean old entries from request tracking."""
        # Remove entries older than 1 minute
        self._minute_requests[key] = [
            ts for ts in self._minute_requests[key]
            if current_time - ts < 60
        ]
        
        # Remove entries older than 1 hour
        self._hour_requests[key] = [
            ts for ts in self._hour_requests[key]
            if current_time - ts < 3600
        ]
    
    def reset(self, identifier: Optional[str] = None, user_id: Optional[str] = None):
        """
        Reset rate limit for an identifier.
        
        Args:
            identifier: Rate limit identifier
            user_id: User ID
        """
        key = user_id or identifier or 'default'
        with self._lock:
            self._minute_requests.pop(key, None)
            self._hour_requests.pop(key, None)

