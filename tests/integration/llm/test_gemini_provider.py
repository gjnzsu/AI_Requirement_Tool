"""
Quick test script to verify Gemini Pro configuration.

Run this to test if Gemini is properly configured before running the full evaluation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.llm import LLMRouter
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.gemini')


def test_gemini():
    """Test Gemini Pro configuration."""
    logger.info("=" * 80)
    logger.info("Testing Gemini Pro Configuration")
    logger.info("=" * 80)
    logger.info("")
    
    # Check configuration
    logger.info("Checking configuration...")
    if Config.LLM_PROVIDER.lower() != 'gemini':
        logger.warning(f"LLM_PROVIDER is set to '{Config.LLM_PROVIDER}', not 'gemini'")
        logger.info("Set it with: $env:LLM_PROVIDER='gemini'")
        return False
    
    api_key = Config.GEMINI_API_KEY
    if not api_key or api_key.startswith('your-'):
        logger.error("GEMINI_API_KEY not set")
        logger.info("Set it with: $env:GEMINI_API_KEY='your-api-key'")
        return False
    
    model = Config.GEMINI_MODEL
    logger.info(f"Provider: {Config.LLM_PROVIDER}")
    logger.info(f"Model: {model}")
    logger.info(f"API Key: {api_key[:10]}...")
    logger.info("")
    
    # Check if package is installed
    logger.info("Checking dependencies...")
    try:
        import google.generativeai as genai
        logger.info("google-generativeai package is installed")
    except ImportError:
        logger.error("google-generativeai package not installed")
        logger.info("Install it with: pip install google-generativeai")
        return False
    
    logger.info("")
    
    # Check proxy configuration
    proxy = Config.GEMINI_PROXY or Config.HTTPS_PROXY or Config.HTTP_PROXY
    if proxy:
        logger.info(f"Proxy configured: {proxy}")
    else:
        logger.info("No proxy configured")
    logger.info("")
    
    # Test API connection
    logger.info("Testing Gemini API connection...")
    try:
        provider_kwargs = {}
        if proxy:
            provider_kwargs['proxy'] = proxy
        
        provider = LLMRouter.get_provider(
            provider_name="gemini",
            api_key=api_key,
            model=model,
            **provider_kwargs
        )
        logger.info(f"Provider initialized: {provider.get_provider_name()}")
        logger.info("")
        
        # Test a simple request
        logger.info("Sending test request to Gemini...")
        response = provider.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello, Gemini is working!' in JSON format: {\"message\": \"...\"}",
            temperature=0.3,
            json_mode=True
        )
        
        logger.info("Response received!")
        logger.info("")
        logger.info("Response:")
        logger.info("-" * 80)
        logger.info(response)
        logger.info("-" * 80)
        logger.info("")
        logger.info("Gemini Pro is configured correctly!")
        return True
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.info("")
        logger.info("Troubleshooting:")
        logger.info("  1. Verify your API key is correct")
        logger.info("  2. Check if you have API quota/credits")
        logger.info("  3. Ensure the model name is correct")
        logger.info("  4. Check your internet connection")
        return False


if __name__ == "__main__":
    success = test_gemini()
    sys.exit(0 if success else 1)

