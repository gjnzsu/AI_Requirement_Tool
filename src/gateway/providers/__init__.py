"""Gateway provider adapters.

Keep this package import light. ``AdapterFactory`` imports ``LLMRouter`` and the
router imports ``GatewayProviderWrapper``; eager imports here create a circular
import that makes gateway support appear unavailable.
"""

from .base_adapter import BaseProviderAdapter

__all__ = [
    'BaseProviderAdapter',
    'AdapterFactory',
    'GatewayProviderWrapper',
]


def __getattr__(name):
    if name == "AdapterFactory":
        from .adapter_factory import AdapterFactory

        return AdapterFactory
    if name == "GatewayProviderWrapper":
        from .gateway_provider_wrapper import GatewayProviderWrapper

        return GatewayProviderWrapper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

