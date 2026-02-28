"""Gateway routing components."""

from .router import Router
from .fallback import FallbackManager
from .circuit_breaker import CircuitBreaker

__all__ = [
    'Router',
    'FallbackManager',
    'CircuitBreaker',
]

