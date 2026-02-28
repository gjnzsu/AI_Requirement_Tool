"""
AI Gateway Service.

This module provides a FastAPI-based gateway for managing LLM provider requests
with rate limiting, caching, metrics, and intelligent routing.
"""

from .gateway_service import GatewayService, create_gateway_app

__all__ = ['GatewayService', 'create_gateway_app']

