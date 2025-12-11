"""
Quick test to verify MCP is enabled and the custom Jira MCP server is available.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.mcp.mcp_integration import MCPIntegration
from src.mcp.mcp_client import create_custom_jira_mcp_client

async def test_mcp_enabled():
    """Test if MCP is enabled and custom server is available."""
    print("=" * 70)
    print("Testing MCP Configuration")
    print("=" * 70)
    print()
    
    # Check config
    print("1. Checking Configuration:")
    print(f"   USE_MCP = {Config.USE_MCP}")
    print(f"   JIRA_URL = {Config.JIRA_URL[:50]}..." if len(Config.JIRA_URL) > 50 else f"   JIRA_URL = {Config.JIRA_URL}")
    print(f"   JIRA_EMAIL = {Config.JIRA_EMAIL}")
    print(f"   JIRA_API_TOKEN = {'***' + Config.JIRA_API_TOKEN[-4:] if len(Config.JIRA_API_TOKEN) > 4 else 'Not set'}")
    print(f"   JIRA_PROJECT_KEY = {Config.JIRA_PROJECT_KEY}")
    print()
    
    # Check if MCP is enabled
    if not Config.USE_MCP:
        print("❌ MCP is DISABLED in configuration")
        print("   Set USE_MCP=true to enable")
        return False
    
    print("✓ MCP is ENABLED in configuration")
    print()
    
    # Test custom Jira MCP client creation
    print("2. Testing Custom Jira MCP Client:")
    try:
        jira_client = create_custom_jira_mcp_client()
        if jira_client:
            print(f"   ✓ Custom Jira MCP client created")
            print(f"   Command: {' '.join(jira_client.command)}")
            print()
            
            # Try to connect
            print("3. Testing MCP Server Connection:")
            try:
                await jira_client.connect()
                print("   ✓ MCP server connected successfully")
                print(f"   Available tools: {', '.join(jira_client.get_tools().keys())}")
                return True
            except Exception as e:
                print(f"   ❌ Failed to connect to MCP server: {e}")
                return False
        else:
            print("   ❌ Could not create custom Jira MCP client")
            print("   Check your Jira credentials in configuration")
            return False
    except Exception as e:
        print(f"   ❌ Error creating MCP client: {e}")
        return False

async def test_mcp_integration():
    """Test MCP integration initialization."""
    print()
    print("=" * 70)
    print("Testing MCP Integration")
    print("=" * 70)
    print()
    
    try:
        integration = MCPIntegration(use_mcp=True)
        print("✓ MCPIntegration created")
        
        print("Initializing MCP servers...")
        await integration.initialize()
        
        if integration._initialized:
            print(f"✓ MCP Integration initialized successfully")
            tools = integration.get_tools()
            print(f"   Available tools: {len(tools)}")
            for tool in tools:
                print(f"     - {tool.name}")
            return True
        else:
            print("⚠ MCP Integration not initialized")
            print("   This might be normal if servers failed to connect")
            return False
    except Exception as e:
        print(f"❌ MCP Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    print("\n")
    
    # Test 1: Check if MCP is enabled
    mcp_enabled = await test_mcp_enabled()
    
    if not mcp_enabled:
        print("\n" + "=" * 70)
        print("MCP is not properly configured. Please:")
        print("1. Set USE_MCP=true (environment variable or .env file)")
        print("2. Verify Jira credentials are set correctly")
        print("=" * 70)
        return
    
    # Test 2: Test MCP integration
    integration_ok = await test_mcp_integration()
    
    print("\n" + "=" * 70)
    if integration_ok:
        print("✅ MCP is ENABLED and WORKING!")
        print("   You can now use MCP tools when creating Jira issues.")
    else:
        print("⚠ MCP is enabled but integration needs attention.")
        print("   Check the errors above for details.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

