"""
Request models for the AI Gateway.

Pydantic models for validating incoming requests.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chat message in the conversation."""
    
    role: Literal['system', 'user', 'assistant'] = Field(
        ...,
        description="The role of the message sender"
    )
    content: str = Field(
        ...,
        description="The content of the message"
    )


class ChatCompletionRequest(BaseModel):
    """Request model for chat completion."""
    
    messages: List[ChatMessage] = Field(
        ...,
        min_length=1,
        description="List of messages in the conversation"
    )
    model: Optional[str] = Field(
        None,
        description="Model to use. If not specified, gateway will select automatically."
    )
    provider: Optional[str] = Field(
        None,
        description="Explicit provider to use ('openai', 'gemini', 'deepseek'). If not specified, gateway will route automatically."
    )
    temperature: Optional[float] = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)"
    )
    max_tokens: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum number of tokens to generate"
    )
    json_mode: Optional[bool] = Field(
        False,
        description="Whether to force JSON response format"
    )
    cache: Optional[bool] = Field(
        True,
        description="Whether to use cached responses if available"
    )
    routing_strategy: Optional[Literal['auto', 'cost', 'latency', 'load', 'explicit']] = Field(
        None,
        description="Routing strategy to use. Overrides global configuration."
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID for rate limiting and metrics tracking"
    )
    timeout: Optional[float] = Field(
        None,
        gt=0,
        description="Request timeout in seconds"
    )

