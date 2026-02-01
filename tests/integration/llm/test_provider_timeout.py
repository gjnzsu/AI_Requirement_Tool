"""
Integration tests for LLM provider timeout parameter support.

Tests that all LLM providers (OpenAI, Gemini, DeepSeek) properly handle
the timeout parameter in generate_response method.
"""

import pytest
import time
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.llm import LLMRouter
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.provider_timeout')


class TestProviderTimeout:
    """Test suite for LLM provider timeout support."""
    
    @pytest.mark.slow
    def test_openai_provider_timeout(self):
        """Test OpenAI provider timeout parameter."""
        if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith('your-'):
            pytest.skip("OpenAI API key not configured")
        
        provider = LLMRouter.get_provider(
            provider_name="openai",
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL
        )
        
        # Test with timeout parameter
        start_time = time.time()
        response = provider.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello' in one word.",
            temperature=0.3,
            timeout=30.0  # 30 second timeout
        )
        elapsed = time.time() - start_time
        
        assert response is not None
        assert len(response) > 0
        assert elapsed < 35.0  # Should complete within timeout + buffer
        logger.info(f"OpenAI response received in {elapsed:.2f}s")
    
    @pytest.mark.slow
    def test_openai_provider_timeout_none(self):
        """Test OpenAI provider with timeout=None (default behavior)."""
        if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith('your-'):
            pytest.skip("OpenAI API key not configured")
        
        provider = LLMRouter.get_provider(
            provider_name="openai",
            api_key=Config.OPENAI_API_KEY,
            model=Config.OPENAI_MODEL
        )
        
        # Test without timeout (should use default)
        response = provider.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello' in one word.",
            temperature=0.3,
            timeout=None
        )
        
        assert response is not None
        assert len(response) > 0
    
    @pytest.mark.slow
    def test_gemini_provider_timeout(self):
        """Test Gemini provider timeout parameter."""
        if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY.startswith('your-'):
            pytest.skip("Gemini API key not configured")
        
        if Config.LLM_PROVIDER.lower() != 'gemini':
            pytest.skip("Gemini not configured as LLM provider")
        
        provider = LLMRouter.get_provider(
            provider_name="gemini",
            api_key=Config.GEMINI_API_KEY,
            model=Config.GEMINI_MODEL
        )
        
        # Test with timeout parameter
        start_time = time.time()
        response = provider.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello' in one word.",
            temperature=0.3,
            timeout=30.0  # 30 second timeout
        )
        elapsed = time.time() - start_time
        
        assert response is not None
        assert len(response) > 0
        assert elapsed < 35.0  # Should complete within timeout + buffer
        logger.info(f"Gemini response received in {elapsed:.2f}s")
    
    @pytest.mark.slow
    def test_deepseek_provider_timeout(self):
        """Test DeepSeek provider timeout parameter."""
        if not Config.DEEPSEEK_API_KEY or Config.DEEPSEEK_API_KEY.startswith('your-'):
            pytest.skip("DeepSeek API key not configured")
        
        provider = LLMRouter.get_provider(
            provider_name="deepseek",
            api_key=Config.DEEPSEEK_API_KEY,
            model=Config.DEEPSEEK_MODEL
        )
        
        # Test with timeout parameter
        start_time = time.time()
        response = provider.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello' in one word.",
            temperature=0.3,
            timeout=30.0  # 30 second timeout
        )
        elapsed = time.time() - start_time
        
        assert response is not None
        assert len(response) > 0
        assert elapsed < 35.0  # Should complete within timeout + buffer
        logger.info(f"DeepSeek response received in {elapsed:.2f}s")
    
    @pytest.mark.slow
    def test_router_timeout_passthrough(self):
        """Test that LLMRouter passes timeout to underlying provider."""
        if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith('your-'):
            pytest.skip("OpenAI API key not configured")
        
        router = LLMRouter()
        
        # Test with timeout
        start_time = time.time()
        response = router.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello' in one word.",
            temperature=0.3,
            timeout=30.0
        )
        elapsed = time.time() - start_time
        
        assert response is not None
        assert len(response) > 0
        assert elapsed < 35.0
        logger.info(f"Router response received in {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

