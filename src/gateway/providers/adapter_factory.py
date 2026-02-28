"""
Adapter factory for creating provider adapters.

Factory pattern for creating and managing provider adapters.
"""

from typing import Dict, Optional
from src.llm.router import LLMRouter
from src.llm.base_provider import LLMProvider
from config.config import Config
from .base_adapter import BaseProviderAdapter
from .openai_adapter import OpenAIAdapter
from .gemini_adapter import GeminiAdapter
from .deepseek_adapter import DeepSeekAdapter


class AdapterFactory:
    """Factory for creating provider adapters."""
    
    # Registry of adapter classes
    _adapters: Dict[str, type] = {
        'openai': OpenAIAdapter,
        'gemini': GeminiAdapter,
        'deepseek': DeepSeekAdapter,
    }
    
    @classmethod
    def create_adapter(
        cls,
        provider_name: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider_instance: Optional[LLMProvider] = None
    ) -> BaseProviderAdapter:
        """
        Create a provider adapter.
        
        Args:
            provider_name: Name of the provider ('openai', 'gemini', 'deepseek')
            api_key: API key for the provider (if provider_instance not provided)
            model: Model name (if provider_instance not provided)
            provider_instance: Existing LLMProvider instance (optional)
            
        Returns:
            BaseProviderAdapter instance
            
        Raises:
            ValueError: If provider name is not recognized
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._adapters:
            available = ", ".join(cls._adapters.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {available}"
            )
        
        # Use provided instance or create new one
        if provider_instance:
            provider = provider_instance
        else:
            if not api_key:
                # Get API key from config
                if provider_name == 'openai':
                    api_key = Config.OPENAI_API_KEY
                    model = model or Config.OPENAI_MODEL
                elif provider_name == 'gemini':
                    api_key = Config.GEMINI_API_KEY
                    model = model or Config.GEMINI_MODEL
                elif provider_name == 'deepseek':
                    api_key = Config.DEEPSEEK_API_KEY
                    model = model or Config.DEEPSEEK_MODEL
                else:
                    raise ValueError(f"No API key configured for provider '{provider_name}'")
            
            if not api_key:
                raise ValueError(f"API key not found for provider '{provider_name}'")
            
            # Create provider instance
            provider = LLMRouter.get_provider(
                provider_name=provider_name,
                api_key=api_key,
                model=model or Config.get_llm_model()
            )
        
        # Create adapter
        adapter_class = cls._adapters[provider_name]
        return adapter_class(provider)
    
    @classmethod
    def list_adapters(cls) -> list:
        """
        List all available adapter types.
        
        Returns:
            List of adapter names
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: type):
        """
        Register a new adapter type.
        
        Args:
            name: Adapter name
            adapter_class: Adapter class that extends BaseProviderAdapter
        """
        if not issubclass(adapter_class, BaseProviderAdapter):
            raise ValueError(f"Adapter class must extend BaseProviderAdapter")
        cls._adapters[name.lower()] = adapter_class

