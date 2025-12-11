"""
Test script to verify OpenAI API connection and diagnose timeout issues.
"""

import os
import sys
from pathlib import Path

# Fix PowerShell encoding issues on Windows
if sys.platform == 'win32':
    import io
    # Set UTF-8 encoding for stdout/stderr in PowerShell
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from openai import OpenAI
import time
from src.utils.logger import get_logger

logger = get_logger('test.openai')

def test_openai_api():
    """Test OpenAI API connection."""
    logger.info("=" * 70)
    logger.info("OpenAI API Connection Test")
    logger.info("=" * 70)
    logger.info("")
    
    # Check API key
    api_key = Config.OPENAI_API_KEY
    if not api_key or api_key.strip() == '':
        logger.error("ERROR: OPENAI_API_KEY not found in configuration")
        logger.info("Set it in .env file or environment variables")
        logger.info("PowerShell: $env:OPENAI_API_KEY='your-api-key'")
        return False
    
    api_key = api_key.strip()  # Remove any whitespace
    
    # Check for placeholder values
    if api_key.lower() in ['your-openai-api-key', 'your_api_key', '']:
        logger.error("ERROR: OPENAI_API_KEY appears to be a placeholder value")
        logger.info("Please set a valid API key in .env file or environment variables")
        return False
    
    if not api_key.startswith('sk-'):
        logger.warning(f"API key format may be invalid (should start with 'sk-')")
        if len(api_key) >= 5:
            logger.info(f"Current key starts with: {api_key[:5]}...")
        else:
            logger.info(f"Current key is too short (length: {len(api_key)})")
    else:
        logger.info(f"API key format looks valid (starts with 'sk-')")
    
    logger.info("")
    
    # Check model name
    model = Config.OPENAI_MODEL
    logger.info(f"Model: {model}")
    
    # Validate model name
    valid_models = ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
    if model not in valid_models:
        logger.warning(f"Model '{model}' may not be valid")
        logger.info(f"Valid models: {', '.join(valid_models)}")
        if model == "gpt-4.1":
            logger.info("Note: 'gpt-4.1' is not a valid OpenAI model name")
            logger.info("Consider using 'gpt-4' or 'gpt-4-turbo' instead")
    else:
        logger.info("Model name is valid")
    
    logger.info("")
    
    # Test basic connectivity first
    logger.info("Testing basic connectivity...")
    try:
        import requests
        response = requests.get("https://api.openai.com/v1/models", timeout=5.0)
        logger.info(f"Can reach OpenAI API (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        logger.error("Cannot reach OpenAI API - connection blocked or no internet")
        logger.info("Check: Internet connection, firewall, proxy settings")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Connection to OpenAI API timed out")
        logger.info("Check: Network speed, firewall, proxy settings")
    except Exception as e:
        logger.warning(f"Connectivity test failed: {e}")
    
    logger.info("")
    
    # Test API connection
    logger.info("Testing API connection with authentication...")
    try:
        # Use a valid model name for testing
        test_model = model if model in valid_models else "gpt-3.5-turbo"
        if model != test_model:
            logger.info(f"Using '{test_model}' instead of '{model}' for testing")
        
        # Initialize client with timeout and retries
        client = OpenAI(api_key=api_key, timeout=10.0, max_retries=1)
        
        start_time = time.time()
        # Make API call (timeout is set on client, not on the call)
        response = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Say 'Hello'"}]
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
            logger.info("  2. Firewall blocking OpenAI API (api.openai.com)")
            logger.info("  3. Corporate proxy blocking the connection")
            logger.info("  4. DNS resolution issues")
            logger.info("  5. SSL/TLS certificate problems")
            logger.info("")
            logger.info("Solutions:")
            logger.info("  1. Check your internet connection")
            logger.info("  2. Test: ping api.openai.com")
            logger.info("  3. Check firewall/proxy settings")
            logger.info("  4. Try: curl https://api.openai.com/v1/models")
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
    try:
        success = test_openai_api()
        logger.info("")
        logger.info("=" * 70)
        if success:
            logger.info("API test passed - LLM should work")
            exit_code = 0
        else:
            logger.error("API test failed - Check the errors above")
            exit_code = 1
        logger.info("=" * 70)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

