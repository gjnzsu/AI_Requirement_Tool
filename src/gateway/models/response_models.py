"""
Response models for the AI Gateway.

Pydantic models for API responses.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = Field(0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(0, description="Number of tokens in the completion")
    total_tokens: int = Field(0, description="Total number of tokens")


class ProviderMetrics(BaseModel):
    """Metrics for a specific provider."""
    
    provider: str = Field(..., description="Provider name")
    request_count: int = Field(0, description="Total number of requests")
    success_count: int = Field(0, description="Number of successful requests")
    error_count: int = Field(0, description="Number of failed requests")
    average_latency_ms: float = Field(0.0, description="Average latency in milliseconds")
    total_tokens: int = Field(0, description="Total tokens processed")


class ChatCompletionChoice(BaseModel):
    """A choice in the chat completion response."""
    
    index: int = Field(0, description="Choice index")
    message: Dict[str, str] = Field(..., description="Message content")
    finish_reason: str = Field("stop", description="Reason for finishing")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""
    
    id: str = Field(..., description="Response ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    choices: List[ChatCompletionChoice] = Field(..., description="Completion choices")
    usage: Optional[Usage] = Field(None, description="Token usage")
    cached: bool = Field(False, description="Whether response was served from cache")
    latency_ms: Optional[float] = Field(None, description="Request latency in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    version: str = Field("1.0.0", description="Gateway version")
    providers: List[str] = Field(..., description="Available providers")
    features: Dict[str, bool] = Field(..., description="Enabled features")


class ProvidersResponse(BaseModel):
    """List of available providers."""
    
    providers: List[Dict[str, Any]] = Field(..., description="Provider information")


class MetricsResponse(BaseModel):
    """Gateway metrics response."""
    
    total_requests: int = Field(0, description="Total requests processed")
    total_errors: int = Field(0, description="Total errors")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate (0.0 to 1.0)")
    provider_metrics: List[ProviderMetrics] = Field(..., description="Per-provider metrics")

