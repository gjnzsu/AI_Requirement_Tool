"""
Circuit breaker implementation.

Implements circuit breaker pattern to prevent cascading failures.
"""

import time
from typing import Dict, Optional
from enum import Enum
from threading import Lock


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for provider health management.
    
    Prevents sending requests to failing providers.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
        enabled: bool = True
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Max calls in half-open state
            enabled: Whether circuit breaker is enabled
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.enabled = enabled
        
        # Per-provider state: {provider: (state, failure_count, last_failure_time, half_open_calls)}
        self._states: Dict[str, tuple[CircuitState, int, float, int]] = {}
        self._lock = Lock()
    
    def is_available(self, provider: str) -> bool:
        """
        Check if provider is available (circuit is closed or half-open).
        
        Args:
            provider: Provider name
            
        Returns:
            True if provider is available, False otherwise
        """
        if not self.enabled:
            return True
        
        with self._lock:
            if provider not in self._states:
                return True
            
            state, failure_count, last_failure_time, half_open_calls = self._states[provider]
            
            if state == CircuitState.CLOSED:
                return True
            
            if state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - last_failure_time >= self.recovery_timeout:
                    # Transition to half-open
                    self._states[provider] = (
                        CircuitState.HALF_OPEN,
                        failure_count,
                        last_failure_time,
                        0
                    )
                    return True
                return False
            
            if state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                return half_open_calls < self.half_open_max_calls
        
        return True
    
    def record_success(self, provider: str):
        """
        Record a successful request.
        
        Args:
            provider: Provider name
        """
        if not self.enabled:
            return
        
        with self._lock:
            if provider not in self._states:
                return
            
            state, _, _, _ = self._states[provider]
            
            if state == CircuitState.HALF_OPEN:
                # Success in half-open: close the circuit
                self._states[provider] = (
                    CircuitState.CLOSED,
                    0,
                    0.0,
                    0
                )
            elif state == CircuitState.CLOSED:
                # Reset failure count on success
                self._states[provider] = (
                    CircuitState.CLOSED,
                    0,
                    0.0,
                    0
                )
    
    def record_failure(self, provider: str):
        """
        Record a failed request.
        
        Args:
            provider: Provider name
        """
        if not self.enabled:
            return
        
        current_time = time.time()
        
        with self._lock:
            if provider not in self._states:
                self._states[provider] = (
                    CircuitState.CLOSED,
                    1,
                    current_time,
                    0
                )
                return
            
            state, failure_count, last_failure_time, half_open_calls = self._states[provider]
            
            if state == CircuitState.HALF_OPEN:
                # Failure in half-open: open the circuit
                self._states[provider] = (
                    CircuitState.OPEN,
                    failure_count + 1,
                    current_time,
                    half_open_calls
                )
            elif state == CircuitState.CLOSED:
                # Increment failure count
                new_failure_count = failure_count + 1
                if new_failure_count >= self.failure_threshold:
                    # Open the circuit
                    self._states[provider] = (
                        CircuitState.OPEN,
                        new_failure_count,
                        current_time,
                        0
                    )
                else:
                    self._states[provider] = (
                        CircuitState.CLOSED,
                        new_failure_count,
                        current_time,
                        0
                    )
    
    def increment_half_open_calls(self, provider: str):
        """
        Increment half-open call counter.
        
        Args:
            provider: Provider name
        """
        if not self.enabled:
            return
        
        with self._lock:
            if provider not in self._states:
                return
            
            state, failure_count, last_failure_time, half_open_calls = self._states[provider]
            
            if state == CircuitState.HALF_OPEN:
                self._states[provider] = (
                    state,
                    failure_count,
                    last_failure_time,
                    half_open_calls + 1
                )
    
    def get_state(self, provider: str) -> CircuitState:
        """
        Get circuit state for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            CircuitState
        """
        with self._lock:
            if provider not in self._states:
                return CircuitState.CLOSED
            return self._states[provider][0]
    
    def reset(self, provider: Optional[str] = None):
        """
        Reset circuit breaker for a provider or all providers.
        
        Args:
            provider: Provider name (None for all)
        """
        with self._lock:
            if provider:
                self._states.pop(provider, None)
            else:
                self._states.clear()

