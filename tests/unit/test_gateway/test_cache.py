"""
Unit tests for cache.
"""

import pytest
import time
from src.gateway.middleware.cache import Cache


class TestCache:
    """Tests for Cache."""
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = Cache(ttl=3600, enabled=True)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = Cache(ttl=1, enabled=True)  # 1 second TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be None after expiration
        assert cache.get("key1") is None
    
    def test_cache_disabled(self):
        """Test that disabled cache doesn't store values."""
        cache = Cache(enabled=False)
        
        cache.set("key1", "value1")
        assert cache.get("key1") is None
    
    def test_cache_delete(self):
        """Test cache delete operation."""
        cache = Cache(enabled=True)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_cache_clear(self):
        """Test cache clear operation."""
        cache = Cache(enabled=True)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_generate_key(self):
        """Test cache key generation."""
        cache = Cache(enabled=True)
        
        messages = [{"role": "user", "content": "Hello"}]
        key1 = cache.generate_key(messages=messages, model="gpt-4", temperature=0.7)
        key2 = cache.generate_key(messages=messages, model="gpt-4", temperature=0.7)
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different inputs should generate different keys
        key3 = cache.generate_key(messages=messages, model="gpt-3.5", temperature=0.7)
        assert key1 != key3
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = Cache(enabled=True)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.get_stats()
        assert stats['size'] == 2
        assert stats['enabled'] is True
        assert stats['ttl'] == 3600  # default TTL

