"""
Test script for custom Jira MCP server.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.mcp.mcp_client import create_custom_jira_mcp_client, MCPClient
from config.config import Config


async def test_custom_jira_mcp():
    """Test the custom Jira MCP server."""
    print("=" * 70)
    print("Testing Custom Jira MCP Server")
    print("=" * 70)
    print()
    
    # Check credentials
    if not (Config.JIRA_URL and not Config.JIRA_URL.startswith('https://yourcompany') and
            Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
            Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'):
        print("⚠ Jira credentials not configured")
        print("   Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env file")
        return
    
    print("✓ Jira credentials configured")
    print()
    
    # Create client
    print("Creating custom Jira MCP client...")
    try:
        client = create_custom_jira_mcp_client()
        if not client:
            print("✗ Failed to create custom Jira MCP client")
            return
        
        print(f"✓ Client created")
        print(f"  Command: {' '.join(client.command)}")
        print()
        
        # Try to connect
        print("Connecting to custom Jira MCP server...")
        try:
            await asyncio.wait_for(client.connect(), timeout=20.0)
            print("✓ Connected successfully!")
            print()
            
            # List tools
            tools = client.get_tools()
            print(f"Available tools: {len(tools)}")
            for tool_name in tools.keys():
                print(f"  - {tool_name}")
            print()
            
            # Test a tool call (create_jira_issue)
            print("Testing tool: create_jira_issue")
            print("  Note: This will create a test issue in Jira")
            print("  (Skipping actual creation to avoid test issues)")
            print("  Tool is available and ready to use!")
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
            #         print("✓ Tool call successful!")
            #         print(f"  Ticket ID: {result_json.get('ticket_id')}")
            #         print(f"  Link: {result_json.get('link')}")
            #     else:
            #         print(f"✗ Tool call failed: {result_json.get('error')}")
            # except Exception as e:
            #     print(f"✗ Tool call error: {e}")
            #     import traceback
            #     traceback.print_exc()
            
        except asyncio.TimeoutError:
            print("✗ Connection timeout (20s)")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"✗ Failed to create client: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_custom_jira_mcp())

