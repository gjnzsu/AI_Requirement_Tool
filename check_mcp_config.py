"""
Quick script to check if USE_MCP is being loaded correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Force reload config
import importlib
if 'config.config' in sys.modules:
    importlib.reload(sys.modules['config.config'])

from config.config import Config
import os

print("=" * 70)
print("Checking MCP Configuration")
print("=" * 70)
print()

# Check .env file
env_file = project_root / '.env'
print(f"1. .env file location: {env_file}")
print(f"   Exists: {env_file.exists()}")
if env_file.exists():
    with open(env_file, 'r') as f:
        content = f.read()
        if 'USE_MCP' in content:
            use_mcp_lines = [line for line in content.split('\n') if 'USE_MCP' in line and not line.strip().startswith('#')]
            print(f"   USE_MCP lines found: {len(use_mcp_lines)}")
            for line in use_mcp_lines:
                print(f"     {line.strip()}")
        else:
            print("   ⚠ USE_MCP not found in .env file!")
print()

# Check environment variable
print("2. Environment variable:")
env_value = os.getenv('USE_MCP')
print(f"   os.getenv('USE_MCP'): {env_value if env_value else 'NOT SET'}")
print()

# Check Config value
print("3. Config value:")
print(f"   Config.USE_MCP: {Config.USE_MCP}")
print(f"   Type: {type(Config.USE_MCP)}")
print()

# Check if it's being evaluated correctly
print("4. Evaluation check:")
use_mcp_str = os.getenv('USE_MCP', 'true')
print(f"   Raw value from env: '{use_mcp_str}'")
print(f"   Lowercase: '{use_mcp_str.lower()}'")
print(f"   Is in ('true', '1', 'yes'): {use_mcp_str.lower() in ('true', '1', 'yes')}")
print()

print("=" * 70)
if Config.USE_MCP:
    print("✅ USE_MCP is ENABLED")
else:
    print("❌ USE_MCP is DISABLED")
    print()
    print("Troubleshooting:")
    print("1. Make sure .env file has: USE_MCP=true")
    print("2. Make sure .env file is in the project root (generative-ai-chatbot/)")
    print("3. Restart your application after changing .env")
    print("4. Check if there's a system environment variable overriding it")
print("=" * 70)

