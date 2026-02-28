"""
AI Gateway Service.

Main FastAPI application for the AI Gateway.
"""

import uuid
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config.gateway_config import GatewayConfig
from .models.request_models import ChatCompletionRequest, ChatMessage
from .models.response_models import (
    ChatCompletionResponse,
    ChatCompletionChoice,
    Usage,
    HealthResponse,
    ProvidersResponse,
    MetricsResponse,
    ProviderMetrics
)
from .providers.adapter_factory import AdapterFactory
from .providers.base_adapter import BaseProviderAdapter
from .middleware.rate_limiter import RateLimiter
from .middleware.cache import Cache
from .middleware.metrics import MetricsCollector
from .middleware.logger import GatewayLogger
from .routing.router import Router
from .routing.fallback import FallbackManager
from .routing.circuit_breaker import CircuitBreaker


class GatewayService:
    """
    AI Gateway service.
    
    Orchestrates LLM provider requests with middleware and routing.
    """
    
    def __init__(self):
        """Initialize gateway service."""
        self.config = GatewayConfig
        
        # Initialize middleware
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.config.GATEWAY_RATE_LIMIT_PER_MINUTE,
            requests_per_hour=self.config.GATEWAY_RATE_LIMIT_PER_HOUR,
            enabled=self.config.GATEWAY_RATE_LIMIT_ENABLED
        )
        
        self.cache = Cache(
            ttl=self.config.GATEWAY_CACHE_TTL,
            enabled=self.config.GATEWAY_CACHE_ENABLED
        )
        
        self.metrics = MetricsCollector(
            enabled=self.config.GATEWAY_METRICS_ENABLED
        )
        
        self.logger = GatewayLogger(
            log_requests=self.config.GATEWAY_LOG_REQUESTS,
            log_responses=self.config.GATEWAY_LOG_RESPONSES
        )
        
        # Initialize routing components
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.GATEWAY_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=self.config.GATEWAY_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
            half_open_max_calls=self.config.GATEWAY_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
            enabled=self.config.GATEWAY_CIRCUIT_BREAKER_ENABLED
        )
        
        self.router = Router(
            strategy=self.config.GATEWAY_ROUTING_STRATEGY,
            metrics_collector=self.metrics,
            circuit_breaker=self.circuit_breaker
        )
        
        self.fallback_manager = FallbackManager(
            max_retries=self.config.GATEWAY_MAX_RETRIES,
            backoff_base=self.config.GATEWAY_RETRY_BACKOFF_BASE,
            enabled=self.config.GATEWAY_FALLBACK_ENABLED,
            circuit_breaker=self.circuit_breaker
        )
        
        # Initialize providers
        self._adapters: List[BaseProviderAdapter] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize provider adapters."""
        from config.config import Config
        
        providers_to_init = ['openai', 'gemini', 'deepseek']
        
        for provider_name in providers_to_init:
            try:
                # Check if API key is available
                if provider_name == 'openai' and Config.OPENAI_API_KEY:
                    adapter = AdapterFactory.create_adapter(provider_name)
                    self._adapters.append(adapter)
                elif provider_name == 'gemini' and Config.GEMINI_API_KEY:
                    adapter = AdapterFactory.create_adapter(provider_name)
                    self._adapters.append(adapter)
                elif provider_name == 'deepseek' and Config.DEEPSEEK_API_KEY:
                    adapter = AdapterFactory.create_adapter(provider_name)
                    self._adapters.append(adapter)
            except Exception as e:
                # Skip providers that can't be initialized
                self.logger.logger.warning(f"Failed to initialize {provider_name}: {e}")
                continue
    
    async def chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Process chat completion request.
        
        Args:
            request: Chat completion request
            
        Returns:
            Chat completion response
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Log request
            self.logger.log_request(
                request_id=request_id,
                method='POST',
                path='/v1/chat/completions',
                user_id=request.user_id,
                provider=request.provider
            )
            
            # Rate limiting
            allowed, retry_after = self.rate_limiter.check_rate_limit(
                user_id=request.user_id
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )
            
            # Cache check
            cache_key = None
            cached_response = None
            if request.cache:
                cache_key = self.cache.generate_key(
                    messages=[msg.model_dump() for msg in request.messages],
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                cached_response = self.cache.get(cache_key)
            
            if cached_response:
                # Return cached response
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_request(
                    provider=cached_response.get('provider', 'unknown'),
                    latency_ms=latency_ms,
                    success=True,
                    cached=True
                )
                
                self.logger.log_response(
                    request_id=request_id,
                    status_code=200,
                    latency_ms=latency_ms,
                    cached=True
                )
                
                return ChatCompletionResponse(
                    id=request_id,
                    created=int(time.time()),
                    model=cached_response.get('model', 'unknown'),
                    provider=cached_response.get('provider', 'unknown'),
                    choices=[
                        ChatCompletionChoice(
                            index=0,
                            message={"role": "assistant", "content": cached_response['content']},
                            finish_reason="stop"
                        )
                    ],
                    usage=Usage(**cached_response.get('usage', {})),
                    cached=True,
                    latency_ms=latency_ms
                )
            
            # Select provider
            try:
                primary_adapter = self.router.select_provider(
                    adapters=self._adapters,
                    explicit_provider=request.provider,
                    routing_strategy=request.routing_strategy
                )
            except ValueError as e:
                raise HTTPException(status_code=503, detail=str(e))
            
            provider_name = primary_adapter.get_provider_name()
            self.logger.log_provider_selection(
                request_id=request_id,
                selected_provider=provider_name,
                strategy=request.routing_strategy or self.config.GATEWAY_ROUTING_STRATEGY
            )
            
            # Get fallback adapters
            fallback_adapters = [
                adapter for adapter in self._adapters
                if adapter.get_provider_name() != provider_name
            ]
            
            # Execute request with fallback
            try:
                result = await self.fallback_manager.execute_with_fallback(
                    primary_adapter=primary_adapter,
                    fallback_adapters=fallback_adapters,
                    messages=[msg.model_dump() for msg in request.messages],
                    temperature=request.temperature or 0.7,
                    max_tokens=request.max_tokens,
                    json_mode=request.json_mode or False,
                    timeout=request.timeout
                )
            except Exception as e:
                # Record error
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_request(
                    provider=provider_name,
                    latency_ms=latency_ms,
                    success=False
                )
                self.logger.log_error(
                    request_id=request_id,
                    error=e,
                    provider=provider_name
                )
                raise HTTPException(status_code=503, detail=f"All providers failed: {str(e)}")
            
            # Cache result
            if request.cache and cache_key:
                self.cache.set(cache_key, result)
            
            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_request(
                provider=result.get('provider', provider_name),
                latency_ms=latency_ms,
                success=True,
                tokens=result.get('usage', {}).get('total_tokens', 0),
                cached=False
            )
            
            # Log response
            self.logger.log_response(
                request_id=request_id,
                status_code=200,
                latency_ms=latency_ms,
                provider=result.get('provider', provider_name)
            )
            
            # Build response
            return ChatCompletionResponse(
                id=request_id,
                created=int(time.time()),
                model=result.get('model', 'unknown'),
                provider=result.get('provider', provider_name),
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message={"role": "assistant", "content": result['content']},
                        finish_reason="stop"
                    )
                ],
                usage=Usage(**result.get('usage', {})),
                cached=False,
                latency_ms=latency_ms
            )
            
        except HTTPException:
            raise
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.logger.log_error(
                request_id=request_id,
                error=e
            )
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    def get_health(self) -> HealthResponse:
        """Get health status."""
        return HealthResponse(
            status="healthy",
            providers=[adapter.get_provider_name() for adapter in self._adapters],
            features={
                'cache': self.config.GATEWAY_CACHE_ENABLED,
                'rate_limiting': self.config.GATEWAY_RATE_LIMIT_ENABLED,
                'fallback': self.config.GATEWAY_FALLBACK_ENABLED,
                'circuit_breaker': self.config.GATEWAY_CIRCUIT_BREAKER_ENABLED,
                'metrics': self.config.GATEWAY_METRICS_ENABLED
            }
        )
    
    def get_providers(self) -> ProvidersResponse:
        """Get list of available providers."""
        providers = []
        for adapter in self._adapters:
            providers.append({
                'name': adapter.get_provider_name(),
                'model': adapter.get_model(),
                'available': self.circuit_breaker.is_available(adapter.get_provider_name()),
                'state': self.circuit_breaker.get_state(adapter.get_provider_name()).value
            })
        return ProvidersResponse(providers=providers)
    
    def get_metrics(self) -> MetricsResponse:
        """Get gateway metrics."""
        summary = self.metrics.get_summary()
        return MetricsResponse(
            total_requests=summary['total_requests'],
            total_errors=summary['total_errors'],
            cache_hit_rate=summary['cache_hit_rate'],
            provider_metrics=summary['provider_metrics']
        )


def create_gateway_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="AI Gateway",
        description="Gateway service for LLM provider management",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize gateway service
    gateway = GatewayService()
    
    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    async def chat_completions(request: ChatCompletionRequest):
        """Chat completion endpoint."""
        return await gateway.chat_completion(request)
    
    @app.get("/v1/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint."""
        return gateway.get_health()
    
    @app.get("/v1/providers", response_model=ProvidersResponse)
    async def providers():
        """List available providers."""
        return gateway.get_providers()
    
    @app.get("/v1/metrics", response_model=MetricsResponse)
    async def metrics():
        """Get gateway metrics."""
        return gateway.get_metrics()
    
    return app

