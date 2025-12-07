"""
Quick test to verify the MCP Pydantic model creation fix.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
from src.mcp.mcp_integration import MCPIntegration
from config.config import Config

async def test_mcp_fix():
    """Test if MCP integration initializes without Pydantic errors."""
    print("=" * 70)
    print("Testing MCP Integration Fix")
    print("=" * 70)
    print()
    
    print("1. Creating MCPIntegration instance...")
    try:
        integration = MCPIntegration(use_mcp=True)
        print("   ✓ MCPIntegration created")
    except Exception as e:
        print(f"   ✗ Failed to create MCPIntegration: {e}")
        return False
    
    print()
    print("2. Initializing MCP servers...")
    try:
        await integration.initialize()
        print("   ✓ MCP Integration initialized successfully")
        
        if integration._initialized:
            tools = integration.get_tools()
            print(f"   ✓ Found {len(tools)} MCP tools")
            for tool in tools:
                print(f"     - {tool.name}")
            return True
        else:
            print("   ⚠ MCP Integration not fully initialized")
            return False
    except Exception as e:
        print(f"   ✗ MCP Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print()
    success = asyncio.run(test_mcp_fix())
    print()
    print("=" * 70)
    if success:
        print("✅ FIX VERIFIED: MCP Integration works correctly!")
    else:
        print("❌ FIX FAILED: MCP Integration still has errors")
    print("=" * 70)

