"""
Unit tests for circuit breaker.
"""

import pytest
import time
from src.gateway.routing.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts in closed state."""
        cb = CircuitBreaker(enabled=True)
        
        assert cb.is_available("provider1") is True
        assert cb.get_state("provider1") == CircuitState.CLOSED
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(
            failure_threshold=3,
            enabled=True
        )
        
        # Record 2 failures (should still be closed)
        cb.record_failure("provider1")
        cb.record_failure("provider1")
        assert cb.is_available("provider1") is True
        
        # 3rd failure should open circuit
        cb.record_failure("provider1")
        assert cb.is_available("provider1") is False
        assert cb.get_state("provider1") == CircuitState.OPEN
    
    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open recovery."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,  # 1 second
            enabled=True
        )
        
        # Open the circuit
        cb.record_failure("provider1")
        cb.record_failure("provider1")
        assert cb.get_state("provider1") == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should transition to half-open
        assert cb.is_available("provider1") is True
        assert cb.get_state("provider1") == CircuitState.HALF_OPEN
    
    def test_circuit_breaker_success_in_half_open_closes(self):
        """Test that success in half-open state closes circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            enabled=True
        )
        
        # Open circuit
        cb.record_failure("provider1")
        cb.record_failure("provider1")
        time.sleep(1.1)  # Wait for recovery
        
        # Trigger transition to half-open (happens inside is_available when timeout passed)
        assert cb.is_available("provider1") is True
        assert cb.get_state("provider1") == CircuitState.HALF_OPEN
        
        # Success should close circuit
        cb.record_success("provider1")
        assert cb.get_state("provider1") == CircuitState.CLOSED
    
    def test_circuit_breaker_failure_in_half_open_reopens(self):
        """Test that failure in half-open state reopens circuit."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            enabled=True
        )
        
        # Open circuit
        cb.record_failure("provider1")
        cb.record_failure("provider1")
        time.sleep(1.1)  # Wait for recovery
        
        # Failure in half-open should reopen
        cb.record_failure("provider1")
        assert cb.get_state("provider1") == CircuitState.OPEN
    
    def test_circuit_breaker_disabled(self):
        """Test that disabled circuit breaker always allows requests."""
        cb = CircuitBreaker(enabled=False)
        
        # Even after many failures, should still be available
        for i in range(10):
            cb.record_failure("provider1")
        
        assert cb.is_available("provider1") is True
    
    def test_circuit_breaker_reset(self):
        """Test circuit breaker reset."""
        cb = CircuitBreaker(
            failure_threshold=2,
            enabled=True
        )
        
        # Open circuit
        cb.record_failure("provider1")
        cb.record_failure("provider1")
        
        # Reset
        cb.reset("provider1")
        
        # Should be available again
        assert cb.is_available("provider1") is True
        assert cb.get_state("provider1") == CircuitState.CLOSED

