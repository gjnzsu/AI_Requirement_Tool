"""
Fallback manager.

Manages automatic fallback to alternative providers on failure.
"""

import asyncio
from typing import List, Optional, Dict, Any
from ..providers.base_adapter import BaseProviderAdapter
from .circuit_breaker import CircuitBreaker


class FallbackManager:
    """
    Manages fallback logic for provider failures.
    
    Implements retry with exponential backoff and fallback chain.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        enabled: bool = True,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize fallback manager.
        
        Args:
            max_retries: Maximum number of retries
            backoff_base: Base for exponential backoff
            enabled: Whether fallback is enabled
            circuit_breaker: Circuit breaker instance
        """
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.enabled = enabled
        self.circuit_breaker = circuit_breaker
    
    async def execute_with_fallback(
        self,
        primary_adapter: BaseProviderAdapter,
        fallback_adapters: List[BaseProviderAdapter],
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute request with automatic fallback.
        
        Args:
            primary_adapter: Primary provider adapter
            fallback_adapters: List of fallback adapters
            messages: List of messages
            temperature: Temperature setting
            max_tokens: Max tokens
            json_mode: JSON mode flag
            timeout: Request timeout
            
        Returns:
            Response dictionary
            
        Raises:
            Exception: If all providers fail
        """
        adapters = [primary_adapter] + fallback_adapters
        last_error = None
        
        for attempt, adapter in enumerate(adapters):
            provider_name = adapter.get_provider_name()
            
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.is_available(provider_name):
                continue
            
            # Calculate backoff delay (exponential)
            if attempt > 0:
                delay = self.backoff_base ** (attempt - 1)
                await asyncio.sleep(delay)
            
            try:
                # Increment half-open calls if in half-open state
                if self.circuit_breaker:
                    self.circuit_breaker.increment_half_open_calls(provider_name)
                
                # Execute request
                result = await adapter.generate_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                    timeout=timeout
                )
                
                # Record success
                if self.circuit_breaker:
                    self.circuit_breaker.record_success(provider_name)
                
                return result
                
            except Exception as e:
                last_error = e
                
                # Record failure
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure(provider_name)
                
                # If this is the last adapter, raise the error
                if adapter == adapters[-1]:
                    break
                
                # Continue to next adapter
                continue
        
        # All providers failed
        raise Exception(
            f"All providers failed. Last error: {str(last_error)}"
        ) from last_error

