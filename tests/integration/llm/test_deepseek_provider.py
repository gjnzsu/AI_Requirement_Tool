"""
Test script to verify DeepSeek API connection and diagnose connectivity issues.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from openai import OpenAI
import time
from src.utils.logger import get_logger

logger = get_logger('test.deepseek')

def test_deepseek_api():
    """Test DeepSeek API connection."""
    logger.info("=" * 70)
    logger.info("DeepSeek API Connection Test")
    logger.info("=" * 70)
    logger.info("")
    
    # Check API key
    api_key = Config.DEEPSEEK_API_KEY
    if not api_key:
        logger.error("ERROR: DEEPSEEK_API_KEY not found in configuration")
        logger.info("Set it in .env file or environment variables")
        return False
    
    if len(api_key) < 10:
        logger.warning(f"API key format may be invalid (too short)")
        logger.info(f"Current key length: {len(api_key)}")
    else:
        logger.info(f"API key format looks valid (length: {len(api_key)})")
    
    logger.info("")
    
    # Check model name
    model = Config.DEEPSEEK_MODEL
    logger.info(f"Model: {model}")
    
    # Validate model name
    valid_models = ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner']
    if model not in valid_models:
        logger.warning(f"Model '{model}' may not be valid")
        logger.info(f"Valid models: {', '.join(valid_models)}")
    else:
        logger.info("Model name is valid")
    
    logger.info("")
    
    # Test basic connectivity first
    logger.info("Testing basic connectivity...")
    try:
        import requests
        response = requests.get("https://api.deepseek.com/v1/models", timeout=5.0)
        logger.info(f"Can reach DeepSeek API (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach DeepSeek API - connection blocked or no internet")
        logger.info("Check: Internet connection, firewall, proxy settings")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Connection to DeepSeek API timed out")
        logger.info("Check: Network speed, firewall, proxy settings")
    except Exception as e:
        logger.warning(f"Connectivity test failed: {e}")
    
    logger.info("")
    
    # Test API connection
    logger.info("Testing API connection with authentication...")
    try:
        # Use a valid model name for testing
        test_model = model if model in valid_models else "deepseek-chat"
        if model != test_model:
            logger.info(f"Using '{test_model}' instead of '{model}' for testing")
        
        # Initialize client with timeout and retries
        # DeepSeek uses OpenAI-compatible API with custom base_url
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=60.0,  # Increased timeout for reliability
            max_retries=1
        )
        
        start_time = time.time()
        # Make API call
        response = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Say 'Hello, DeepSeek is working!'"}]
        )
        elapsed = time.time() - start_time
        
        logger.info("API call successful!")
        logger.info(f"Response time: {elapsed:.2f} seconds")
        logger.info(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        logger.error(f"API call failed: {e}")
        logger.info(f"Error type: {type(e).__name__}")
        
        # Check for specific error types
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        if "connection" in error_type.lower() or "connection" in error_str:
            logger.info("This is a connection error")
            logger.info("Possible causes:")
            logger.info("  1. No internet connection")
            logger.info("  2. Firewall blocking DeepSeek API (api.deepseek.com)")
            logger.info("  3. Corporate proxy blocking the connection")
            logger.info("  4. DNS resolution issues")
            logger.info("  5. SSL/TLS certificate problems")
            logger.info("")
            logger.info("Solutions:")
            logger.info("  1. Check your internet connection")
            logger.info("  2. Test: ping api.deepseek.com")
            logger.info("  3. Check firewall/proxy settings")
            logger.info("  4. Try: curl https://api.deepseek.com/v1/models")
            logger.info("  5. If behind proxy, set HTTP_PROXY/HTTPS_PROXY environment variables")
        elif "timeout" in error_str:
            logger.info("This is a timeout error")
            logger.info("Check: Network connection, firewall, proxy settings")
        elif "401" in str(e) or "unauthorized" in error_str:
            logger.info("This is an authentication error")
            logger.info("Check: API key is valid and not expired")
        elif "404" in str(e) or "not found" in error_str:
            logger.info("This is a model not found error")
            logger.info("Check: Model name is correct and you have access")
        elif "rate limit" in error_str:
            logger.info("This is a rate limit error")
            logger.info("Check: You've exceeded your API quota")
        
        # Try to get more details from the exception
        if hasattr(e, 'response'):
            logger.info(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
        if hasattr(e, 'request'):
            logger.info(f"Request URL: {e.request.url if hasattr(e.request, 'url') else 'N/A'}")
        
        return False

if __name__ == "__main__":
    success = test_deepseek_api()
    logger.info("")
    logger.info("=" * 70)
    if success:
        logger.info("API test passed - DeepSeek LLM should work")
    else:
        logger.error("API test failed - Check the errors above")
    logger.info("=" * 70)
    sys.exit(0 if success else 1)
