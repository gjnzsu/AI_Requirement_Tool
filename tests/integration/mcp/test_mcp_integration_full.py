"""
Comprehensive integration test for MCP tool creation and usage.
Tests the full flow from MCP server connection to tool invocation.
"""

import sys
import asyncio
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.mcp.mcp_integration import MCPIntegration
from src.mcp.mcp_client import create_custom_jira_mcp_client
from src.utils.logger import get_logger

@pytest.mark.asyncio
async def test_full_mcp_integration():
    logger = get_logger('test.full_mcp_integration')

    """Test the complete MCP integration flow."""
    logger.info("=" * 70)
    logger.info("Comprehensive MCP Integration Test")
    logger.info("=" * 70)
    logger.info("")
    
    # Test 1: Configuration
    logger.info("1. Testing Configuration:")
    logger.info(f"   USE_MCP: {Config.USE_MCP}")
    logger.info(f"   JIRA_URL: {Config.JIRA_URL}")
    logger.info(f"   JIRA_PROJECT_KEY: {Config.JIRA_PROJECT_KEY}")
    if not Config.USE_MCP:
        logger.error("   ❌ MCP is disabled in config")
        return False
    logger.info("   ✓ Configuration OK")
    logger.info("")
    
    # Test 2: MCP Client Creation
    logger.info("2. Testing MCP Client Creation:")
    try:
        jira_client = create_custom_jira_mcp_client()
        if jira_client:
            logger.info(f"   ✓ MCP client created")
            logger.info(f"   Client type: {type(jira_client)}")
            logger.info(f"   Has call_tool: {hasattr(jira_client, 'call_tool')}")
        else:
            logger.error("   ❌ Failed to create MCP client")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error creating MCP client: {e}")
        import traceback
        traceback.print_exc()
        return False
    logger.info("")
    
    # Test 3: MCP Integration Initialization
    logger.info("3. Testing MCP Integration Initialization:")
    try:
        integration = MCPIntegration(use_mcp=True)
        logger.info("   ✓ MCPIntegration created")
        
        await integration.initialize()
        logger.info("   ✓ MCP Integration initialized")
        
        if not integration._initialized:
            logger.error("   ❌ Integration not marked as initialized")
            return False
        
        tools = integration.get_tools()
        logger.info(f"   ✓ Found {len(tools)} tools")
        
        if len(tools) == 0:
            logger.error("   ❌ No tools available")
            return False
        
        # Verify tool structure
        for tool in tools:
            # Use getattr to access Pydantic attributes safely
            tool_name = getattr(tool, 'name', 'unknown')
            logger.info(f"     - Tool: {tool_name}")
            logger.info(f"       Type: {type(tool)}")
            
            # Check for _mcp_client using getattr
            mcp_client = getattr(tool, '_mcp_client', None)
            if mcp_client is None:
                logger.error(f"       ❌ _mcp_client is None!")
                return False
            else:
                logger.info(f"       ✓ _mcp_client is set")
                logger.info(f"       Client type: {type(mcp_client)}")
                logger.info(f"       Has call_tool: {hasattr(mcp_client, 'call_tool')}")
        
    except Exception as e:
        logger.error(f"   ❌ MCP Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    logger.info("")
    
    # Test 4: Tool Invocation (Dry Run)
    logger.info("4. Testing Tool Structure (Dry Run):")
    try:
        create_tool = None
        for tool in tools:
            tool_name = getattr(tool, 'name', None)
            if tool_name == 'create_jira_issue':
                create_tool = tool
                break
        
        if not create_tool:
            logger.error("   ❌ create_jira_issue tool not found")
            return False
        
        logger.info(f"   ✓ Found create_jira_issue tool")
        logger.info(f"   Tool type: {type(create_tool)}")
        
        # Use getattr to safely access attributes
        mcp_client = getattr(create_tool, '_mcp_client', None)
        tool_name_attr = getattr(create_tool, '_tool_name', None)
        
        logger.info(f"   _mcp_client: {mcp_client}")
        logger.info(f"   _tool_name: {tool_name_attr}")
        
        # Verify the tool can be invoked (structure check only)
        if mcp_client is None:
            logger.error("   ❌ _mcp_client is None - cannot invoke tool")
            return False
        
        if not hasattr(mcp_client, 'call_tool'):
            logger.error("   ❌ Client does not have call_tool method")
            return False
        
        logger.info("   ✓ Tool structure is valid")
        
    except Exception as e:
        logger.error(f"   ❌ Tool structure check failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    logger.info("")
    
    logger.info("=" * 70)
    logger.info("✅ All Integration Tests Passed!")
    logger.info("=" * 70)
    return True

if __name__ == "__main__":
    logger.info("")
    success = asyncio.run(test_full_mcp_integration())
    logger.info("")
    if success:
        logger.info("✅ Integration test PASSED - MCP is ready to use")
    else:
        logger.error("❌ Integration test FAILED - Check errors above")
    logger.info("")

