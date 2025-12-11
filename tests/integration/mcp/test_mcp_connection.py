"""
Test script to verify MCP server connection.

This script tests the updated Jira MCP integration with actual working packages:
- mcp-jira (by Warzuponus)
- mcp-atlassian (by Sooperset)
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.mcp_integration import MCPIntegration
from src.mcp.mcp_client import create_jira_mcp_client, create_confluence_mcp_client

async def test_mcp_connection():
    logger = get_logger('test.mcp_connection')

    """Test MCP server connections."""
    logger.info("=" * 70)
    logger.info("Testing MCP Server Connections")
    logger.info("=" * 70)
    logger.info("")
    
    # Test 1: Check npx availability
    logger.info("Test 1: Checking npx availability...")
    integration = MCPIntegration(use_mcp=True)
    npx_available = integration._check_npx_available()
    logger.info(f"  npx available: {npx_available}")
    logger.info("")
    
    if not npx_available:
        logger.error("❌ npx is not available. Cannot test MCP servers.")
        logger.info("   Please ensure Node.js is installed and npx is in PATH.")
        return
    
    # Test 2: Try to create Jira MCP client
    logger.info("Test 2: Creating Jira MCP client...")
    try:
        jira_client = create_jira_mcp_client()
        if jira_client:
            logger.info(f"  ✓ Jira MCP client created")
            logger.info(f"  Command: {' '.join(jira_client.command)}")
            
            # Try to connect
            logger.info("  Attempting to connect...")
            try:
                await jira_client.connect()
                logger.info("  ✓ Successfully connected to Jira MCP server!")
                logger.info(f"  Available tools: {list(jira_client.get_tools().keys())}")
            except Exception as e:
                logger.error(f"  ✗ Connection failed: {e}")
                logger.error(f"  Error type: {type(e).__name__}")
        else:
            logger.warning("  ⚠ Jira MCP client not created (credentials may not be configured)")
    except Exception as e:
        logger.error(f"  ✗ Failed to create Jira MCP client: {e}")
    
    logger.info("")
    
    # Test 3: Try to create Confluence MCP client
    logger.info("Test 3: Creating Confluence MCP client...")
    try:
        confluence_client = create_confluence_mcp_client()
        if confluence_client:
            logger.info(f"  ✓ Confluence MCP client created")
            logger.info(f"  Command: {' '.join(confluence_client.command)}")
            
            # Try to connect
            logger.info("  Attempting to connect...")
            try:
                await confluence_client.connect()
                logger.info("  ✓ Successfully connected to Confluence MCP server!")
                logger.info(f"  Available tools: {list(confluence_client.get_tools().keys())}")
            except Exception as e:
                logger.error(f"  ✗ Connection failed: {e}")
                logger.error(f"  Error type: {type(e).__name__}")
        else:
            logger.warning("  ⚠ Confluence MCP client not created (credentials may not be configured)")
    except Exception as e:
        logger.error(f"  ✗ Failed to create Confluence MCP client: {e}")
    
    logger.info("")
    
    # Test 4: Test full MCP integration
    logger.info("Test 4: Testing full MCP integration...")
    try:
        integration = MCPIntegration(use_mcp=True)
        await integration.initialize()
        
        if integration._initialized:
            logger.info(f"  ✓ MCP Integration initialized successfully!")
            logger.info(f"  Available tools: {len(integration.tools)}")
            for tool in integration.tools:
                logger.info(f"    - {tool.name}: {tool.description[:50]}...")
        else:
            logger.warning("  ⚠ MCP Integration not initialized (falling back to custom tools)")
    except Exception as e:
        logger.error(f"  ✗ MCP Integration failed: {e}")
        import traceback
from src.utils.logger import get_logger

        traceback.print_exc()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Complete")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Summary:")
    logger.info("- If MCP servers connect: MCP protocol is working!")
    logger.info("- If MCP servers fail: Chatbot will use custom tools (still works!)")
    logger.info("- Custom tools are always available as fallback")
    logger.info("")
    logger.info("Available MCP Server Packages:")
    logger.info("  ⭐ Atlassian Rovo MCP Server (Official - Recommended)")
    logger.info("     npm install -g mcp-remote")
    logger.info("     https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/")
    logger.info("")
    logger.info("  - mcp-jira (npm install -g mcp-jira)")
    logger.info("  - mcp-atlassian (npm install -g mcp-atlassian)")
    logger.info("")
    logger.info("See JIRA_MCP_INTEGRATION.md for detailed setup instructions.")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())

