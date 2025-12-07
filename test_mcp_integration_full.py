"""
Comprehensive integration test for MCP tool creation and usage.
Tests the full flow from MCP server connection to tool invocation.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.mcp.mcp_integration import MCPIntegration
from src.mcp.mcp_client import create_custom_jira_mcp_client

async def test_full_mcp_integration():
    """Test the complete MCP integration flow."""
    print("=" * 70)
    print("Comprehensive MCP Integration Test")
    print("=" * 70)
    print()
    
    # Test 1: Configuration
    print("1. Testing Configuration:")
    print(f"   USE_MCP: {Config.USE_MCP}")
    print(f"   JIRA_URL: {Config.JIRA_URL}")
    print(f"   JIRA_PROJECT_KEY: {Config.JIRA_PROJECT_KEY}")
    if not Config.USE_MCP:
        print("   ❌ MCP is disabled in config")
        return False
    print("   ✓ Configuration OK")
    print()
    
    # Test 2: MCP Client Creation
    print("2. Testing MCP Client Creation:")
    try:
        jira_client = create_custom_jira_mcp_client()
        if jira_client:
            print(f"   ✓ MCP client created")
            print(f"   Client type: {type(jira_client)}")
            print(f"   Has call_tool: {hasattr(jira_client, 'call_tool')}")
        else:
            print("   ❌ Failed to create MCP client")
            return False
    except Exception as e:
        print(f"   ❌ Error creating MCP client: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test 3: MCP Integration Initialization
    print("3. Testing MCP Integration Initialization:")
    try:
        integration = MCPIntegration(use_mcp=True)
        print("   ✓ MCPIntegration created")
        
        await integration.initialize()
        print("   ✓ MCP Integration initialized")
        
        if not integration._initialized:
            print("   ❌ Integration not marked as initialized")
            return False
        
        tools = integration.get_tools()
        print(f"   ✓ Found {len(tools)} tools")
        
        if len(tools) == 0:
            print("   ❌ No tools available")
            return False
        
        # Verify tool structure
        for tool in tools:
            # Use getattr to access Pydantic attributes safely
            tool_name = getattr(tool, 'name', 'unknown')
            print(f"     - Tool: {tool_name}")
            print(f"       Type: {type(tool)}")
            
            # Check for _mcp_client using getattr
            mcp_client = getattr(tool, '_mcp_client', None)
            if mcp_client is None:
                print(f"       ❌ _mcp_client is None!")
                return False
            else:
                print(f"       ✓ _mcp_client is set")
                print(f"       Client type: {type(mcp_client)}")
                print(f"       Has call_tool: {hasattr(mcp_client, 'call_tool')}")
        
    except Exception as e:
        print(f"   ❌ MCP Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    # Test 4: Tool Invocation (Dry Run)
    print("4. Testing Tool Structure (Dry Run):")
    try:
        create_tool = None
        for tool in tools:
            tool_name = getattr(tool, 'name', None)
            if tool_name == 'create_jira_issue':
                create_tool = tool
                break
        
        if not create_tool:
            print("   ❌ create_jira_issue tool not found")
            return False
        
        print(f"   ✓ Found create_jira_issue tool")
        print(f"   Tool type: {type(create_tool)}")
        
        # Use getattr to safely access attributes
        mcp_client = getattr(create_tool, '_mcp_client', None)
        tool_name_attr = getattr(create_tool, '_tool_name', None)
        
        print(f"   _mcp_client: {mcp_client}")
        print(f"   _tool_name: {tool_name_attr}")
        
        # Verify the tool can be invoked (structure check only)
        if mcp_client is None:
            print("   ❌ _mcp_client is None - cannot invoke tool")
            return False
        
        if not hasattr(mcp_client, 'call_tool'):
            print("   ❌ Client does not have call_tool method")
            return False
        
        print("   ✓ Tool structure is valid")
        
    except Exception as e:
        print(f"   ❌ Tool structure check failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    print()
    
    print("=" * 70)
    print("✅ All Integration Tests Passed!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    print()
    success = asyncio.run(test_full_mcp_integration())
    print()
    if success:
        print("✅ Integration test PASSED - MCP is ready to use")
    else:
        print("❌ Integration test FAILED - Check errors above")
    print()

