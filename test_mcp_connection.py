"""
Test script to verify MCP server connection.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.mcp.mcp_integration import MCPIntegration
from src.mcp.mcp_client import create_jira_mcp_client, create_confluence_mcp_client

async def test_mcp_connection():
    """Test MCP server connections."""
    print("=" * 70)
    print("Testing MCP Server Connections")
    print("=" * 70)
    print()
    
    # Test 1: Check npx availability
    print("Test 1: Checking npx availability...")
    integration = MCPIntegration(use_mcp=True)
    npx_available = integration._check_npx_available()
    print(f"  npx available: {npx_available}")
    print()
    
    if not npx_available:
        print("❌ npx is not available. Cannot test MCP servers.")
        print("   Please ensure Node.js is installed and npx is in PATH.")
        return
    
    # Test 2: Try to create Jira MCP client
    print("Test 2: Creating Jira MCP client...")
    try:
        jira_client = create_jira_mcp_client()
        if jira_client:
            print(f"  ✓ Jira MCP client created")
            print(f"  Command: {' '.join(jira_client.command)}")
            
            # Try to connect
            print("  Attempting to connect...")
            try:
                await jira_client.connect()
                print("  ✓ Successfully connected to Jira MCP server!")
                print(f"  Available tools: {list(jira_client.get_tools().keys())}")
            except Exception as e:
                print(f"  ✗ Connection failed: {e}")
                print(f"  Error type: {type(e).__name__}")
        else:
            print("  ⚠ Jira MCP client not created (credentials may not be configured)")
    except Exception as e:
        print(f"  ✗ Failed to create Jira MCP client: {e}")
    
    print()
    
    # Test 3: Try to create Confluence MCP client
    print("Test 3: Creating Confluence MCP client...")
    try:
        confluence_client = create_confluence_mcp_client()
        if confluence_client:
            print(f"  ✓ Confluence MCP client created")
            print(f"  Command: {' '.join(confluence_client.command)}")
            
            # Try to connect
            print("  Attempting to connect...")
            try:
                await confluence_client.connect()
                print("  ✓ Successfully connected to Confluence MCP server!")
                print(f"  Available tools: {list(confluence_client.get_tools().keys())}")
            except Exception as e:
                print(f"  ✗ Connection failed: {e}")
                print(f"  Error type: {type(e).__name__}")
        else:
            print("  ⚠ Confluence MCP client not created (credentials may not be configured)")
    except Exception as e:
        print(f"  ✗ Failed to create Confluence MCP client: {e}")
    
    print()
    
    # Test 4: Test full MCP integration
    print("Test 4: Testing full MCP integration...")
    try:
        integration = MCPIntegration(use_mcp=True)
        await integration.initialize()
        
        if integration._initialized:
            print(f"  ✓ MCP Integration initialized successfully!")
            print(f"  Available tools: {len(integration.tools)}")
            for tool in integration.tools:
                print(f"    - {tool.name}: {tool.description[:50]}...")
        else:
            print("  ⚠ MCP Integration not initialized (falling back to custom tools)")
    except Exception as e:
        print(f"  ✗ MCP Integration failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)
    print()
    print("Summary:")
    print("- If MCP servers connect: MCP protocol is working!")
    print("- If MCP servers fail: Chatbot will use custom tools (still works!)")
    print("- Custom tools are always available as fallback")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())

