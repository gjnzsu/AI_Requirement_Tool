"""
LLM Callback Handlers for Monitoring and Observability.

This module provides callback handlers for tracking LLM performance,
token usage, and costs.
"""

from typing import Dict, Any, Optional
import time
from datetime import datetime
try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
    except ImportError:
        # Fallback: create a dummy base class if neither import works
        class BaseCallbackHandler:
            """Dummy callback handler if langchain callbacks not available."""
            pass
from src.utils.logger import get_logger

logger = get_logger('chatbot.agent.callbacks')


class LLMMonitoringCallback(BaseCallbackHandler):
    """
    Lightweight callback for monitoring LLM calls.
    
    Tracks:
    - Performance (latency)
    - Token usage (for cost estimation)
    - Errors
    
    All methods are wrapped with try/except to ensure callbacks
    never break the main LLM flow.
    """
    
    def __init__(self):
        """Initialize the monitoring callback."""
        super().__init__()
        self.start_time: Optional[float] = None
        self.call_count = 0
        self.total_tokens = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_duration = 0.0
        self.error_count = 0
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: list, **kwargs):
        """Called when LLM call starts."""
        try:
            self.start_time = time.time()
            self.call_count += 1
            
            # Log basic info at debug level (safely)
            try:
                model_name = 'unknown'
                if serialized and isinstance(serialized, dict):
                    id_field = serialized.get('id', [])
                    if isinstance(id_field, list) and id_field:
                        model_name = id_field[-1]
                    elif isinstance(id_field, str):
                        model_name = id_field
                logger.debug(f"LLM call #{self.call_count} started: {model_name}")
                if prompts:
                    logger.debug(f"Prompts: {len(prompts)} prompt(s)")
            except Exception as e:
                logger.debug(f"LLM call #{self.call_count} started (error logging details: {e})")
        except Exception as e:
            logger.warning(f"Error in on_llm_start callback: {e}")
    
    def on_llm_end(self, response: Any, **kwargs):
        """Called when LLM call completes successfully."""
        try:
            if self.start_time is None:
                return
            
            duration = time.time() - self.start_time
            self.total_duration += duration
            
            # Extract token usage if available (safely)
            token_usage = {}
            try:
                if hasattr(response, 'llm_output') and response.llm_output:
                    llm_output = response.llm_output
                    if isinstance(llm_output, dict) and 'token_usage' in llm_output:
                        token_usage = llm_output['token_usage']
                elif hasattr(response, 'response_metadata') and response.response_metadata:
                    metadata = response.response_metadata
                    if isinstance(metadata, dict) and 'token_usage' in metadata:
                        token_usage = metadata['token_usage']
            except Exception as e:
                logger.debug(f"Could not extract token usage: {e}")
            
            # Track tokens (safely)
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            
            if isinstance(token_usage, dict):
                prompt_tokens = token_usage.get('prompt_tokens', 0) or 0
                completion_tokens = token_usage.get('completion_tokens', 0) or 0
                total_tokens = token_usage.get('total_tokens', 0) or (prompt_tokens + completion_tokens)
            
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            
            # Log performance and cost info
            logger.info(
                f"LLM call #{self.call_count} completed: "
                f"{duration:.2f}s | "
                f"Tokens: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens})"
            )
            
            self.start_time = None
        except Exception as e:
            logger.warning(f"Error in on_llm_end callback: {e}")
            self.start_time = None
    
    def on_llm_error(self, error: Exception, **kwargs):
        """Called when LLM call fails."""
        try:
            self.error_count += 1
            duration = time.time() - self.start_time if self.start_time else 0
            
            logger.error(
                f"LLM call #{self.call_count} failed after {duration:.2f}s: {error}"
            )
            
            self.start_time = None
        except Exception as e:
            logger.warning(f"Error in on_llm_error callback: {e}")
            self.start_time = None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        try:
            avg_duration = self.total_duration / self.call_count if self.call_count > 0 else 0
            success_rate = ((self.call_count - self.error_count) / self.call_count * 100) if self.call_count > 0 else 0
            
            return {
                'total_calls': self.call_count,
                'successful_calls': self.call_count - self.error_count,
                'error_count': self.error_count,
                'success_rate': f"{success_rate:.1f}%",
                'total_tokens': self.total_tokens,
                'total_prompt_tokens': self.total_prompt_tokens,
                'total_completion_tokens': self.total_completion_tokens,
                'total_duration_seconds': round(self.total_duration, 2),
                'average_duration_seconds': round(avg_duration, 2),
                'estimated_cost_usd': self._estimate_cost()
            }
        except Exception as e:
            logger.warning(f"Error getting statistics: {e}")
            return {
                'total_calls': 0,
                'successful_calls': 0,
                'error_count': 0,
                'success_rate': "0.0%",
                'total_tokens': 0,
                'total_prompt_tokens': 0,
                'total_completion_tokens': 0,
                'total_duration_seconds': 0,
                'average_duration_seconds': 0,
                'estimated_cost_usd': 0.0
            }
    
    def _estimate_cost(self) -> float:
        """Estimate cost based on token usage."""
        try:
            prompt_cost_per_1k = 0.0015
            completion_cost_per_1k = 0.002
            
            prompt_cost = (self.total_prompt_tokens / 1000) * prompt_cost_per_1k
            completion_cost = (self.total_completion_tokens / 1000) * completion_cost_per_1k
            
            return round(prompt_cost + completion_cost, 4)
        except Exception:
            return 0.0
    
    def log_summary(self):
        """Log a summary of all monitored calls."""
        try:
            stats = self.get_statistics()
            logger.info("=" * 70)
            logger.info("LLM Monitoring Summary")
            logger.info("=" * 70)
            logger.info(f"Total Calls: {stats.get('total_calls', 0)}")
            logger.info(f"Successful: {stats.get('successful_calls', 0)} | Errors: {stats.get('error_count', 0)}")
            logger.info(f"Success Rate: {stats.get('success_rate', '0%')}")
            logger.info(f"Total Tokens: {stats.get('total_tokens', 0):,}")
            logger.info(f"  - Prompt: {stats.get('total_prompt_tokens', 0):,}")
            logger.info(f"  - Completion: {stats.get('total_completion_tokens', 0):,}")
            logger.info(f"Total Duration: {stats.get('total_duration_seconds', 0):.2f}s")
            logger.info(f"Average Duration: {stats.get('average_duration_seconds', 0):.2f}s")
            logger.info(f"Estimated Cost: ${stats.get('estimated_cost_usd', 0):.4f}")
            logger.info("=" * 70)
        except Exception as e:
            logger.warning(f"Error logging summary: {e}")
