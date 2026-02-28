"""
LLM Provider Router/Factory.

This module provides a factory pattern to create and manage different LLM providers.
"""

from typing import Dict, Optional, Type
from .base_provider import LLMProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider

# Try to import gateway provider wrapper (optional)
try:
    from src.gateway.providers.gateway_provider_wrapper import GatewayProviderWrapper
    GATEWAY_AVAILABLE = True
except ImportError:
    GATEWAY_AVAILABLE = False
    GatewayProviderWrapper = None


class LLMRouter:
    """
    Router/Factory for LLM providers.
    
    Manages multiple LLM providers and routes requests to the appropriate one.
    """
    
    # Registry of available providers
    _providers: Dict[str, Type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "deepseek": DeepSeekProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[LLMProvider]):
        """
        Register a new LLM provider.
        
        Args:
            name: Provider name/identifier
            provider_class: Provider class that implements LLMProvider
        """
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def get_provider(cls, provider_name: str, api_key: str, model: str, **kwargs) -> LLMProvider:
        """
        Get an instance of the specified LLM provider.
        
        Args:
            provider_name: Name of the provider ('openai', 'gemini', 'deepseek')
            api_key: API key for the provider
            model: Model name/identifier
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If provider name is not recognized
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        return provider_class(api_key=api_key, model=model, **kwargs)
    
    @classmethod
    def list_providers(cls) -> list:
        """
        List all registered providers.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """
        Check if a provider is available.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            True if provider is available, False otherwise
        """
        provider_name = provider_name.lower()
        if provider_name == 'gateway':
            return GATEWAY_AVAILABLE
        return provider_name in cls._providers
    
    @classmethod
    def get_gateway_provider(cls, model: Optional[str] = None, provider: Optional[str] = None) -> Optional[LLMProvider]:
        """
        Get a gateway provider wrapper if gateway is enabled.
        
        Args:
            model: Model name (optional)
            provider: Provider name (optional)
            
        Returns:
            GatewayProviderWrapper instance or None if gateway not available
        """
        if not GATEWAY_AVAILABLE or GatewayProviderWrapper is None:
            return None
        
        try:
            from config.config import Config
            if not Config.GATEWAY_ENABLED:
                return None
            return GatewayProviderWrapper(model=model, provider=provider)
        except Exception:
            return None


class LLMProviderManager:
    """
    Manager for LLM providers with fallback support.
    
    Can manage multiple providers and automatically fallback if one fails.
    """
    
    def __init__(self, primary_provider: LLMProvider, 
                 fallback_providers: Optional[list] = None):
        """
        Initialize the provider manager.
        
        Args:
            primary_provider: Primary LLM provider to use
            fallback_providers: Optional list of fallback providers
        """
        self.primary = primary_provider
        self.fallbacks = fallback_providers or []
    
    def generate_response(self, system_prompt: str, user_prompt: str,
                         temperature: float = 0.3, json_mode: bool = False,
                         timeout: float = None) -> str:
        """
        Generate response with automatic fallback.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Sampling temperature
            json_mode: Whether to use JSON mode
            timeout: Override timeout for this request (seconds). Default uses provider timeout.
            
        Returns:
            Generated response
            
        Raises:
            Exception: If all providers fail
        """
        providers = [self.primary] + self.fallbacks
        
        for provider in providers:
            try:
                return provider.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    json_mode=json_mode,
                    timeout=timeout
                )
            except Exception as e:
                if provider == providers[-1]:  # Last provider
                    raise e
                print(f"Provider {provider.get_provider_name()} failed: {e}")
                print(f"Falling back to next provider...")
                continue
        
        raise Exception("All providers failed")

