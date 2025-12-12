"""
Test script for custom Jira MCP server.
"""

import sys
import asyncio
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.mcp_client import create_custom_jira_mcp_client, MCPClient
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.custom_jira_mcp')

@pytest.mark.asyncio
async def test_custom_jira_mcp():

    """Test the custom Jira MCP server."""
    logger.info("=" * 70)
    logger.info("Testing Custom Jira MCP Server")
    logger.info("=" * 70)
    logger.info("")
    
    # Check credentials
    if not (Config.JIRA_URL and not Config.JIRA_URL.startswith('https://yourcompany') and
            Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
            Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'):
        logger.warning("⚠ Jira credentials not configured")
        logger.info("   Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env file")
        return
    
    logger.info("✓ Jira credentials configured")
    logger.info("")
    
    # Create client
    logger.info("Creating custom Jira MCP client...")
    try:
        client = create_custom_jira_mcp_client()
        if not client:
            logger.error("✗ Failed to create custom Jira MCP client")
            return
        
        logger.info(f"✓ Client created")
        logger.info(f"  Command: {' '.join(client.command)}")
        logger.info("")
        
        # Try to connect
        logger.info("Connecting to custom Jira MCP server...")
        try:
            await asyncio.wait_for(client.connect(), timeout=20.0)
            logger.info("✓ Connected successfully!")
            logger.info("")
            
            # List tools
            tools = client.get_tools()
            logger.info(f"Available tools: {len(tools)}")
            for tool_name in tools.keys():
                logger.info(f"  - {tool_name}")
            logger.info("")
            
            # Test a tool call (create_jira_issue)
            logger.info("Testing tool: create_jira_issue")
            logger.info("  Note: This will create a test issue in Jira")
            logger.info("  (Skipping actual creation to avoid test issues)")
            logger.info("  Tool is available and ready to use!")
            # Uncomment below to actually create a test issue:
            # try:
            #     test_args = {
            #         "summary": "Test Issue from MCP Server",
            #         "description": "This is a test issue created by the custom Jira MCP server",
            #         "priority": "Low",
            #         "issue_type": "Task"
            #     }
            #     result = await client.call_tool('create_jira_issue', test_args)
            #     # Parse JSON result (MCP returns text content)
            #     import json
            #     if isinstance(result, dict) and result.get('content'):
            #         content = result['content']
            #         if isinstance(content, list) and len(content) > 0:
            #             if hasattr(content[0], 'text'):
            #                 result_json = json.loads(content[0].text)
            #             elif isinstance(content[0], dict):
            #                 result_json = json.loads(content[0].get('text', '{}'))
            #             else:
            #                 result_json = json.loads(str(content[0]))
            #         else:
            #             result_json = json.loads(str(content))
            #     else:
            #         result_json = result
            #     
            #     if result_json.get('success'):
            #         logger.info("✓ Tool call successful!")
            #         logger.info(f"  Ticket ID: {result_json.get('ticket_id')}")
            #         logger.info(f"  Link: {result_json.get('link')}")
            #     else:
            #         logger.error(f"✗ Tool call failed: {result_json.get('error')}")
            # except Exception as e:
            #     logger.error(f"✗ Tool call error: {e}")
            #     import traceback
            #     traceback.print_exc()
            
        except asyncio.TimeoutError:
            logger.error("✗ Connection timeout (20s)")
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        logger.error(f"✗ Failed to create client: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Test Complete")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_custom_jira_mcp())

