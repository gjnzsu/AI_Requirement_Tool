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
    logger = get_logger('test.mcp_enabled')

    """Test if MCP is enabled and custom server is available."""
    logger.info("=" * 70)
    logger.info("Testing MCP Configuration")
    logger.info("=" * 70)
    logger.info("")
    
    # Check config
    logger.info("1. Checking Configuration:")
    logger.info(f"   USE_MCP = {Config.USE_MCP}")
    logger.info(f"   JIRA_URL = {Config.JIRA_URL[:50]}..." if len(Config.JIRA_URL) > 50 else f"   JIRA_URL = {Config.JIRA_URL}")
    logger.info(f"   JIRA_EMAIL = {Config.JIRA_EMAIL}")
    logger.info(f"   JIRA_API_TOKEN = {'***' + Config.JIRA_API_TOKEN[-4:] if len(Config.JIRA_API_TOKEN) > 4 else 'Not set'}")
    logger.info(f"   JIRA_PROJECT_KEY = {Config.JIRA_PROJECT_KEY}")
    logger.info("")
    
    # Check if MCP is enabled
    if not Config.USE_MCP:
        logger.error("❌ MCP is DISABLED in configuration")
        logger.info("   Set USE_MCP=true to enable")
        return False
    
    logger.info("✓ MCP is ENABLED in configuration")
    logger.info("")
    
    # Test custom Jira MCP client creation
    logger.info("2. Testing Custom Jira MCP Client:")
    try:
        jira_client = create_custom_jira_mcp_client()
        if jira_client:
            logger.info(f"   ✓ Custom Jira MCP client created")
            logger.info(f"   Command: {' '.join(jira_client.command)}")
            logger.info("")
            
            # Try to connect
            logger.info("3. Testing MCP Server Connection:")
            try:
                await jira_client.connect()
                logger.info("   ✓ MCP server connected successfully")
                logger.info(f"   Available tools: {', '.join(jira_client.get_tools().keys())}")
                return True
            except Exception as e:
                logger.error(f"   ❌ Failed to connect to MCP server: {e}")
                return False
        else:
            logger.error("   ❌ Could not create custom Jira MCP client")
            logger.info("   Check your Jira credentials in configuration")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error creating MCP client: {e}")
        return False

async def test_mcp_integration():
    """Test MCP integration initialization."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Testing MCP Integration")
    logger.info("=" * 70)
    logger.info("")
    
    try:
        integration = MCPIntegration(use_mcp=True)
        logger.info("✓ MCPIntegration created")
        
        logger.info("Initializing MCP servers...")
        await integration.initialize()
        
        if integration._initialized:
            logger.info(f"✓ MCP Integration initialized successfully")
            tools = integration.get_tools()
            logger.info(f"   Available tools: {len(tools)}")
            for tool in tools:
                logger.info(f"     - {tool.name}")
            return True
        else:
            logger.warning("⚠ MCP Integration not initialized")
            logger.error("   This might be normal if servers failed to connect")
            return False
    except Exception as e:
        logger.error(f"❌ MCP Integration failed: {e}")
        import traceback
from src.utils.logger import get_logger

        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    logger.info("\n")
    
    # Test 1: Check if MCP is enabled
    mcp_enabled = await test_mcp_enabled()
    
    if not mcp_enabled:
        logger.info("\n" + "=" * 70)
        logger.info("MCP is not properly configured. Please:")
        logger.info("1. Set USE_MCP=true (environment variable or .env file)")
        logger.info("2. Verify Jira credentials are set correctly")
        logger.info("=" * 70)
        return
    
    # Test 2: Test MCP integration
    integration_ok = await test_mcp_integration()
    
    logger.info("\n" + "=" * 70)
    if integration_ok:
        logger.info("✅ MCP is ENABLED and WORKING!")
        logger.info("   You can now use MCP tools when creating Jira issues.")
    else:
        logger.warning("⚠ MCP is enabled but integration needs attention.")
        logger.error("   Check the errors above for details.")
    logger.info("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

