"""
Custom Jira MCP Server - Simplified Version.

This is a Python-based MCP server that provides Jira issue creation.
Only exposes the create_jira_issue tool that returns the ticket ID.
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Any, Sequence

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    # Try different import paths for MCP SDK
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
        MCP_SERVER_AVAILABLE = True
    except ImportError:
        try:
            from mcp import Server
            from mcp.server.stdio import stdio_server
            from mcp.types import Tool, TextContent
            MCP_SERVER_AVAILABLE = True
        except ImportError:
            MCP_SERVER_AVAILABLE = False
except ImportError:
    MCP_SERVER_AVAILABLE = False

from config.config import Config
from src.tools.jira_tool import JiraTool

# Global Jira connection
jira_tool = None
jira_client = None


def initialize_jira():
    """Initialize Jira connection."""
    global jira_tool, jira_client
    try:
        jira_tool = JiraTool()
        jira_client = jira_tool.jira
        print("✓ Jira connection initialized", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Failed to initialize Jira connection: {e}", file=sys.stderr)
        raise


# Initialize server
if MCP_SERVER_AVAILABLE:
    server = Server("jira-mcp-server")
else:
    server = None


async def create_jira_issue(args: dict) -> dict:
    """Create a Jira issue and return the ticket ID."""
    import datetime
    
    # Log that MCP server is being used
    print(f"🔵 MCP Server: Creating Jira issue - {args.get('summary', '')[:50]}...", file=sys.stderr)
    
    summary = args.get("summary", "")
    description = args.get("description", "")
    priority = args.get("priority", "Medium")
    issue_type = args.get("issue_type", "Story")
    
    if not summary:
        return {"success": False, "error": "Summary is required"}
    
    try:
        issue_dict = {
            'project': {'key': Config.JIRA_PROJECT_KEY},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
            'priority': {'name': priority}
        }
        
        new_issue = jira_client.create_issue(fields=issue_dict)
        print(f"✅ MCP Server: Created issue {new_issue.key}", file=sys.stderr)
        
        # Return simplified response with ticket ID
        return {
            "success": True,
            "ticket_id": new_issue.key,  # e.g., "PROJ-123"
            "issue_key": new_issue.key,
            "link": f"{Config.JIRA_URL}/browse/{new_issue.key}",
            "created_by": "MCP_SERVER",  # Add identifier
            "tool_used": "custom-jira-mcp-server"  # Add tool identifier
        }
    except Exception as e:
        print(f"❌ MCP SERVER: Error creating issue: {e}", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return {"success": False, "error": str(e)}


# Register tools
if MCP_SERVER_AVAILABLE and server:
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="create_jira_issue",
                description="Create a new Jira issue and return the ticket ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Issue summary/title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Issue priority (High, Medium, Low)",
                            "enum": ["High", "Medium", "Low"],
                            "default": "Medium"
                        },
                        "issue_type": {
                            "type": "string",
                            "description": "Issue type (Story, Task, Bug, Epic)",
                            "enum": ["Story", "Task", "Bug", "Epic"],
                            "default": "Story"
                        }
                    },
                    "required": ["summary", "description"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Handle tool calls."""
        try:
            if name == "create_jira_issue":
                result = await create_jira_issue(arguments)
            else:
                result = {"success": False, "error": f"Unknown tool: {name}"}
            
            # Format result as JSON string
            result_text = json.dumps(result, indent=2, default=str)
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            error_result = {"success": False, "error": str(e)}
            error_text = json.dumps(error_result, indent=2)
            return [TextContent(type="text", text=error_text)]


async def main():
    """Main entry point for the MCP server."""
    if not MCP_SERVER_AVAILABLE:
        print("Error: MCP server SDK not installed. Install with: pip install mcp", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Initialize Jira connection
        initialize_jira()
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        print(f"Error starting Jira MCP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
