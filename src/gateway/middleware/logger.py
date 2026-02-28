"""
Logging middleware.

Structured logging for gateway requests and responses.
"""

import json
import time
from typing import Optional, Dict, Any
from src.utils.logger import get_logger


class GatewayLogger:
    """
    Logger for gateway operations.
    
    Provides structured logging for requests, responses, and errors.
    """
    
    def __init__(
        self,
        log_requests: bool = True,
        log_responses: bool = False
    ):
        """
        Initialize gateway logger.
        
        Args:
            log_requests: Whether to log requests
            log_responses: Whether to log responses (disabled by default for privacy)
        """
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.logger = get_logger('gateway')
    
    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ):
        """
        Log an incoming request.
        
        Args:
            request_id: Unique request ID
            method: HTTP method
            path: Request path
            user_id: User ID (if available)
            provider: Provider name (if selected)
            **kwargs: Additional request metadata
        """
        if not self.log_requests:
            return
        
        log_data = {
            'type': 'request',
            'request_id': request_id,
            'method': method,
            'path': path,
            'timestamp': time.time(),
        }
        
        if user_id:
            log_data['user_id'] = user_id
        if provider:
            log_data['provider'] = provider
        
        log_data.update(kwargs)
        
        self.logger.info(f"Request: {json.dumps(log_data)}")
    
    def log_response(
        self,
        request_id: str,
        status_code: int,
        latency_ms: float,
        provider: Optional[str] = None,
        cached: bool = False,
        **kwargs
    ):
        """
        Log a response.
        
        Args:
            request_id: Request ID
            status_code: HTTP status code
            latency_ms: Request latency in milliseconds
            provider: Provider used
            cached: Whether response was cached
            **kwargs: Additional response metadata
        """
        if not self.log_requests:
            return
        
        log_data = {
            'type': 'response',
            'request_id': request_id,
            'status_code': status_code,
            'latency_ms': latency_ms,
            'timestamp': time.time(),
        }
        
        if provider:
            log_data['provider'] = provider
        if cached:
            log_data['cached'] = cached
        
        log_data.update(kwargs)
        
        self.logger.info(f"Response: {json.dumps(log_data)}")
    
    def log_error(
        self,
        request_id: str,
        error: Exception,
        provider: Optional[str] = None,
        **kwargs
    ):
        """
        Log an error.
        
        Args:
            request_id: Request ID
            error: Exception that occurred
            provider: Provider that failed
            **kwargs: Additional error metadata
        """
        log_data = {
            'type': 'error',
            'request_id': request_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': time.time(),
        }
        
        if provider:
            log_data['provider'] = provider
        
        log_data.update(kwargs)
        
        self.logger.error(f"Error: {json.dumps(log_data)}", exc_info=True)
    
    def log_provider_selection(
        self,
        request_id: str,
        selected_provider: str,
        strategy: str,
        reason: Optional[str] = None
    ):
        """
        Log provider selection.
        
        Args:
            request_id: Request ID
            selected_provider: Selected provider name
            strategy: Routing strategy used
            reason: Reason for selection
        """
        if not self.log_requests:
            return
        
        log_data = {
            'type': 'provider_selection',
            'request_id': request_id,
            'provider': selected_provider,
            'strategy': strategy,
            'timestamp': time.time(),
        }
        
        if reason:
            log_data['reason'] = reason
        
        self.logger.debug(f"Provider Selection: {json.dumps(log_data)}")

