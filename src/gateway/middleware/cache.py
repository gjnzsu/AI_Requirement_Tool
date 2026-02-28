"""
Cache middleware.

Implements response caching for gateway requests.
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
from threading import Lock


class Cache:
    """
    Response cache for gateway requests.
    
    Supports in-memory caching with TTL.
    """
    
    def __init__(self, ttl: int = 3600, enabled: bool = True):
        """
        Initialize cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
            enabled: Whether caching is enabled
        """
        self.ttl = ttl
        self.enabled = enabled
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None
        
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp = self._cache[key]
            
            # Check if expired
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: Any):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if not self.enabled:
            return
        
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def delete(self, key: str):
        """
        Delete value from cache.
        
        Args:
            key: Cache key
        """
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    def generate_key(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate cache key from request parameters.
        
        Args:
            messages: List of messages
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens
            system_prompt: System prompt
            
        Returns:
            Cache key string
        """
        # Create hashable representation
        key_data = {
            'messages': messages,
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'system_prompt': system_prompt
        }
        
        # Convert to JSON string and hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            # Clean expired entries
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp > self.ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            
            return {
                'size': len(self._cache),
                'ttl': self.ttl,
                'enabled': self.enabled
            }

