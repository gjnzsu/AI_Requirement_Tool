"""
Gemini provider adapter.

Adapter for Google Gemini LLM provider.
"""

import asyncio
from typing import Optional, Dict, Any
from .base_adapter import BaseProviderAdapter


class GeminiAdapter(BaseProviderAdapter):
    """Adapter for Gemini provider."""
    
    async def generate_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate completion using Gemini provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Whether to force JSON response
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with 'content', 'usage', and metadata
        """
        # Extract system prompt and user prompt
        system_prompt, user_prompt = self._extract_system_prompt(messages)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        try:
            # Execute provider call in thread pool
            response_text = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.provider.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        json_mode=json_mode,
                        timeout=timeout
                    )
                ),
                timeout=timeout or 60.0
            )
            
            # Estimate token usage
            prompt_tokens = self._estimate_tokens(system_prompt + user_prompt)
            completion_tokens = self._estimate_tokens(response_text)
            
            return {
                'content': response_text,
                'usage': {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens
                },
                'model': self.model,
                'provider': self.provider_name
            }
        except asyncio.TimeoutError:
            raise TimeoutError(f"Gemini request timed out after {timeout or 60.0} seconds")
        except Exception as e:
            raise Exception(f"Gemini provider error: {str(e)}") from e

