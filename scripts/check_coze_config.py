"""
Diagnostic script to check Coze API configuration and test authentication.

This script helps identify configuration issues with Coze API integration.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding issues
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('coze.diagnostic')

# Use ASCII-safe checkmarks for Windows compatibility
CHECK = "[OK]"
CROSS = "[X]"
WARN = "[!]"


def check_coze_configuration():
    """Check Coze configuration and provide diagnostic information."""
    print("=" * 70)
    print("Coze API Configuration Diagnostic")
    print("=" * 70)
    print()
    
    # Check environment variables
    print("1. Environment Variables Check:")
    print("-" * 70)
    coze_enabled = os.getenv('COZE_ENABLED', '').lower()
    coze_token = os.getenv('COZE_API_TOKEN', '')
    coze_bot_id = os.getenv('COZE_BOT_ID', '')
    coze_base_url = os.getenv('COZE_API_BASE_URL', '')
    
    print(f"   COZE_ENABLED: {coze_enabled} {CHECK if coze_enabled in ('true', '1', 'yes') else CROSS + ' (not enabled)'}")
    print(f"   COZE_API_TOKEN: {CHECK + ' Set' if coze_token else CROSS + ' NOT SET'}")
    if coze_token:
        print(f"      Token preview: {coze_token[:10]}...{coze_token[-5:] if len(coze_token) > 15 else ''}")
        print(f"      Token length: {len(coze_token)} characters")
    print(f"   COZE_BOT_ID: {CHECK + ' Set' if coze_bot_id else CROSS + ' NOT SET'}")
    if coze_bot_id:
        print(f"      Bot ID: {coze_bot_id}")
    print(f"   COZE_API_BASE_URL: {coze_base_url or Config.COZE_API_BASE_URL}")
    print()
    
    # Check Config class values
    print("2. Config Class Values:")
    print("-" * 70)
    print(f"   Config.COZE_ENABLED: {Config.COZE_ENABLED}")
    print(f"   Config.COZE_API_TOKEN: {CHECK + ' Set' if Config.COZE_API_TOKEN else CROSS + ' NOT SET'}")
    if Config.COZE_API_TOKEN:
        print(f"      Token preview: {Config.COZE_API_TOKEN[:10]}...{Config.COZE_API_TOKEN[-5:] if len(Config.COZE_API_TOKEN) > 15 else ''}")
    print(f"   Config.COZE_BOT_ID: {CHECK + ' Set' if Config.COZE_BOT_ID else CROSS + ' NOT SET'}")
    if Config.COZE_BOT_ID:
        print(f"      Bot ID: {Config.COZE_BOT_ID}")
    print(f"   Config.COZE_API_BASE_URL: {Config.COZE_API_BASE_URL}")
    print()
    
    # Check CozeClient initialization
    print("3. CozeClient Initialization Check:")
    print("-" * 70)
    client = None
    try:
        from src.services.coze_client import CozeClient
        client = CozeClient()
        print(f"   Client initialized: {CHECK}")
        print(f"   Base URL: {client.base_url}")
        print(f"   Is configured: {CHECK + ' Yes' if client.is_configured() else CROSS + ' No'}")
        
        if client.is_configured():
            print(f"   API Token: {CHECK + ' Present' if client.api_token else CROSS + ' Missing'}")
            print(f"   Bot ID: {CHECK + ' Present' if client.bot_id else CROSS + ' Missing'}")
        else:
            print()
            print(f"   {WARN} Coze client is not properly configured!")
            print("   Please set COZE_API_TOKEN and COZE_BOT_ID environment variables.")
    except ImportError as e:
        print(f"   {CROSS} Error: cozepy SDK not installed")
        print(f"   Install with: pip install cozepy")
        print(f"   Error details: {e}")
    except Exception as e:
        print(f"   {CROSS} Error initializing client: {e}")
        import traceback
        print(f"   Details: {traceback.format_exc()}")
    print()
    
    # Test API endpoint format
    print("4. API Endpoint Information:")
    print("-" * 70)
    if client and client.is_configured():
        # Note: With SDK, endpoint is handled internally, but we show what it would be
        print(f"   Base URL: {client.base_url}")
        print(f"   SDK Method: coze.chat.create() or coze.chat.stream()")
        print(f"   Auth: TokenAuth (handled by SDK)")
        print()
        
        # Check token format
        print("5. Token Format Check:")
        print("-" * 70)
        token = client.api_token
        if token:
            # Common token formats
            if token.startswith('pat-'):
                print(f"   {CHECK} Token appears to be a Personal Access Token (PAT) format")
            elif token.startswith('cztei_'):
                print(f"   {CHECK} Token appears to be a Coze API token format")
            elif token.startswith('sk-'):
                print(f"   {CHECK} Token appears to be an API key format")
            elif len(token) > 50:
                print(f"   {CHECK} Token is a long token (likely valid format)")
            else:
                print(f"   {WARN} Token seems short - verify it's complete")
            print(f"   Token starts with: {token[:6]}...")
            print(f"   Token ends with: ...{token[-6:]}")
        print()
        
        # Check SDK availability
        print("6. SDK Availability Check:")
        print("-" * 70)
        try:
            import cozepy
            print(f"   {CHECK} cozepy SDK is installed")
            print(f"   SDK version: {getattr(cozepy, '__version__', 'unknown')}")
        except ImportError:
            print(f"   {CROSS} cozepy SDK is NOT installed")
            print("   Install with: pip install cozepy")
            print("   See: https://github.com/coze-dev/coze-py")
        print()
        
        # Provide troubleshooting steps
        print("7. Troubleshooting Steps:")
        print("-" * 70)
        print("   If you're getting 401 errors:")
        print("   1. Verify your token is correct:")
        print("      - Log in to Coze platform (https://www.coze.com)")
        print("      - Go to API Management / Developer Console")
        print("      - Copy the API token")
        print("      - Ensure there are no extra spaces or newlines")
        print()
        print("   2. Verify your Bot ID:")
        print("      - Go to your Coze project")
        print("      - Select the bot/agent you want to use")
        print("      - Copy the Bot ID (from URL or bot settings)")
        print("      - Ensure the bot is published with API access enabled")
        print()
        print("   3. Check SDK installation:")
        print("      - Run: pip install cozepy")
        print("      - Verify: python -c 'import cozepy; print(cozepy.__version__)'")
        print()
        print("   4. Verify API endpoint:")
        print("      - For coze.com: https://api.coze.com")
        print("      - For coze.cn: https://api.coze.cn")
        print("      - Set COZE_API_BASE_URL if using China region")
    else:
        print(f"   {WARN} Cannot check endpoint - client not configured")
        print()
        print("   Install SDK:")
        print("   pip install cozepy")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    check_coze_configuration()

