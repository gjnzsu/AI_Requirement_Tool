"""
Quick test to verify the MCP Pydantic model creation fix.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from src.mcp.mcp_integration import MCPIntegration
from config.config import Config

async def test_mcp_fix():
    logger = get_logger('test.mcp_fix')

    """Test if MCP integration initializes without Pydantic errors."""
    logger.info("=" * 70)
    logger.info("Testing MCP Integration Fix")
    logger.info("=" * 70)
    logger.info("")
    
    logger.info("1. Creating MCPIntegration instance...")
    try:
        integration = MCPIntegration(use_mcp=True)
        logger.info("   ✓ MCPIntegration created")
    except Exception as e:
        logger.error(f"   ✗ Failed to create MCPIntegration: {e}")
        return False
    
    logger.info("")
    logger.info("2. Initializing MCP servers...")
    try:
        await integration.initialize()
        logger.info("   ✓ MCP Integration initialized successfully")
        
        if integration._initialized:
            tools = integration.get_tools()
            logger.info(f"   ✓ Found {len(tools)} MCP tools")
            for tool in tools:
                logger.info(f"     - {tool.name}")
            return True
        else:
            logger.warning("   ⚠ MCP Integration not fully initialized")
            return False
    except Exception as e:
        logger.error(f"   ✗ MCP Integration failed: {e}")
        import traceback
from src.utils.logger import get_logger

        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("")
    success = asyncio.run(test_mcp_fix())
    logger.info("")
    logger.info("=" * 70)
    if success:
        logger.info("✅ FIX VERIFIED: MCP Integration works correctly!")
    else:
        logger.error("❌ FIX FAILED: MCP Integration still has errors")
    logger.info("=" * 70)

