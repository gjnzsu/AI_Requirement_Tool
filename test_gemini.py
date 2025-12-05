"""
Quick test script to verify Gemini Pro configuration.

Run this to test if Gemini is properly configured before running the full evaluation.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.llm import LLMRouter
from config.config import Config


def test_gemini():
    """Test Gemini Pro configuration."""
    print("=" * 80)
    print("Testing Gemini Pro Configuration")
    print("=" * 80)
    print()
    
    # Check configuration
    print("Checking configuration...")
    if Config.LLM_PROVIDER.lower() != 'gemini':
        print(f"  ⚠ LLM_PROVIDER is set to '{Config.LLM_PROVIDER}', not 'gemini'")
        print("  Set it with: $env:LLM_PROVIDER='gemini'")
        return False
    
    api_key = Config.GEMINI_API_KEY
    if not api_key or api_key.startswith('your-'):
        print("  ✗ GEMINI_API_KEY not set")
        print("  Set it with: $env:GEMINI_API_KEY='your-api-key'")
        return False
    
    model = Config.GEMINI_MODEL
    print(f"  ✓ Provider: {Config.LLM_PROVIDER}")
    print(f"  ✓ Model: {model}")
    print(f"  ✓ API Key: {api_key[:10]}...")
    print()
    
    # Check if package is installed
    print("Checking dependencies...")
    try:
        import google.generativeai as genai
        print("  ✓ google-generativeai package is installed")
    except ImportError:
        print("  ✗ google-generativeai package not installed")
        print("  Install it with: pip install google-generativeai")
        return False
    
    print()
    
    # Check proxy configuration
    proxy = Config.GEMINI_PROXY or Config.HTTPS_PROXY or Config.HTTP_PROXY
    if proxy:
        print(f"  ✓ Proxy configured: {proxy}")
    else:
        print("  ℹ No proxy configured")
    print()
    
    # Test API connection
    print("Testing Gemini API connection...")
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
        print(f"  ✓ Provider initialized: {provider.get_provider_name()}")
        print()
        
        # Test a simple request
        print("Sending test request to Gemini...")
        response = provider.generate_response(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say 'Hello, Gemini is working!' in JSON format: {\"message\": \"...\"}",
            temperature=0.3,
            json_mode=True
        )
        
        print("  ✓ Response received!")
        print()
        print("Response:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        print()
        print("✅ Gemini Pro is configured correctly!")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        print()
        print("Troubleshooting:")
        print("  1. Verify your API key is correct")
        print("  2. Check if you have API quota/credits")
        print("  3. Ensure the model name is correct")
        print("  4. Check your internet connection")
        return False


if __name__ == "__main__":
    success = test_gemini()
    sys.exit(0 if success else 1)

