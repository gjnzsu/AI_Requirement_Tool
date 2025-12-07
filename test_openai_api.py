"""
Test script to verify OpenAI API connection and diagnose timeout issues.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config
from openai import OpenAI
import time

def test_openai_api():
    """Test OpenAI API connection."""
    print("=" * 70)
    print("OpenAI API Connection Test")
    print("=" * 70)
    print()
    
    # Check API key
    api_key = Config.OPENAI_API_KEY
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in configuration")
        print("   Set it in .env file or environment variables")
        return False
    
    if not api_key.startswith('sk-'):
        print(f"⚠ WARNING: API key format may be invalid (should start with 'sk-')")
        print(f"   Current key starts with: {api_key[:5]}...")
    else:
        print(f"✓ API key format looks valid (starts with 'sk-')")
    
    print()
    
    # Check model name
    model = Config.OPENAI_MODEL
    print(f"Model: {model}")
    
    # Validate model name
    valid_models = ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo']
    if model not in valid_models:
        print(f"⚠ WARNING: Model '{model}' may not be valid")
        print(f"   Valid models: {', '.join(valid_models)}")
        if model == "gpt-4.1":
            print(f"   Note: 'gpt-4.1' is not a valid OpenAI model name")
            print(f"   Consider using 'gpt-4' or 'gpt-4-turbo' instead")
    else:
        print(f"✓ Model name is valid")
    
    print()
    
    # Test basic connectivity first
    print("Testing basic connectivity...")
    try:
        import requests
        response = requests.get("https://api.openai.com/v1/models", timeout=5.0)
        print(f"✓ Can reach OpenAI API (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot reach OpenAI API - connection blocked or no internet")
        print("   Check: Internet connection, firewall, proxy settings")
        return False
    except requests.exceptions.Timeout:
        print("⚠ Connection to OpenAI API timed out")
        print("   Check: Network speed, firewall, proxy settings")
    except Exception as e:
        print(f"⚠ Connectivity test failed: {e}")
    
    print()
    
    # Test API connection
    print("Testing API connection with authentication...")
    try:
        # Use a valid model name for testing
        test_model = model if model in valid_models else "gpt-3.5-turbo"
        if model != test_model:
            print(f"   Using '{test_model}' instead of '{model}' for testing")
        
        # Initialize client with timeout and retries
        client = OpenAI(api_key=api_key, timeout=10.0, max_retries=1)
        
        start_time = time.time()
        # Make API call (timeout is set on client, not on the call)
        response = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Say 'Hello'"}]
        )
        elapsed = time.time() - start_time
        
        print(f"✓ API call successful!")
        print(f"  Response time: {elapsed:.2f} seconds")
        print(f"  Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check for specific error types
        error_str = str(e).lower()
        error_type = type(e).__name__
        
        if "connection" in error_type.lower() or "connection" in error_str:
            print("   → This is a connection error")
            print("   → Possible causes:")
            print("     1. No internet connection")
            print("     2. Firewall blocking OpenAI API (api.openai.com)")
            print("     3. Corporate proxy blocking the connection")
            print("     4. DNS resolution issues")
            print("     5. SSL/TLS certificate problems")
            print()
            print("   → Solutions:")
            print("     1. Check your internet connection")
            print("     2. Test: ping api.openai.com")
            print("     3. Check firewall/proxy settings")
            print("     4. Try: curl https://api.openai.com/v1/models")
            print("     5. If behind proxy, set HTTP_PROXY/HTTPS_PROXY environment variables")
        elif "timeout" in error_str:
            print("   → This is a timeout error")
            print("   → Check: Network connection, firewall, proxy settings")
        elif "401" in str(e) or "unauthorized" in error_str:
            print("   → This is an authentication error")
            print("   → Check: API key is valid and not expired")
        elif "404" in str(e) or "not found" in error_str:
            print("   → This is a model not found error")
            print("   → Check: Model name is correct and you have access")
        elif "rate limit" in error_str:
            print("   → This is a rate limit error")
            print("   → Check: You've exceeded your API quota")
        
        # Try to get more details from the exception
        if hasattr(e, 'response'):
            print(f"   → Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
        if hasattr(e, 'request'):
            print(f"   → Request URL: {e.request.url if hasattr(e.request, 'url') else 'N/A'}")
        
        return False

if __name__ == "__main__":
    success = test_openai_api()
    print()
    print("=" * 70)
    if success:
        print("✓ API test passed - LLM should work")
    else:
        print("❌ API test failed - Check the errors above")
    print("=" * 70)
    sys.exit(0 if success else 1)

