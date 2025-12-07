"""
MCP Client for connecting to MCP servers.

This client connects to MCP servers (like Jira/Confluence MCP servers)
and exposes their tools for use in the chatbot.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    # Try different import paths for MCP SDK
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        MCP_AVAILABLE = True
    except ImportError:
        try:
            from mcp.client import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client
            MCP_AVAILABLE = True
        except ImportError:
            MCP_AVAILABLE = False
except ImportError:
    MCP_AVAILABLE = False
    print("⚠ MCP SDK not installed. Install with: pip install mcp")

from config.config import Config


class MCPClient:
    """
    MCP Client for connecting to MCP servers.
    
    This client connects to MCP servers and provides access to their tools.
    """
    
    def __init__(self, server_name: str, command: List[str], env: Optional[Dict] = None):
        """
        Initialize MCP client.
        
        Args:
            server_name: Name of the MCP server
            command: Command to start the MCP server (e.g., ['npx', '-y', '@modelcontextprotocol/server-jira'])
            env: Environment variables for the server
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed. Install with: pip install mcp")
        
        self.server_name = server_name
        self.command = command
        self.env = env or {}
        self.session: Optional[ClientSession] = None
        self.tools: Dict[str, Any] = {}
        self._initialized = False
    
    async def connect(self):
        """Connect to the MCP server."""
        if self._initialized:
            return
        
        try:
            # Create server parameters
            # Handle Windows .cmd extension
            import platform
            command_exec = self.command[0]
            if platform.system() == 'Windows' and command_exec == 'npx':
                command_exec = 'npx.cmd'
            
            server_params = StdioServerParameters(
                command=command_exec,
                args=self.command[1:] if len(self.command) > 1 else [],
                env=self.env
            )
            
            # Create stdio client and connect
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    
                    # Initialize the session
                    await session.initialize()
                    
                    # List available tools
                    try:
                        tools_result = await session.list_tools()
                        if hasattr(tools_result, 'tools'):
                            self.tools = {tool.name: tool for tool in tools_result.tools}
                        else:
                            # Handle different response formats
                            self.tools = {tool.name: tool for tool in tools_result}
                    except Exception as e:
                        print(f"⚠ Could not list tools from {self.server_name}: {e}")
                        self.tools = {}
                    
                    self._initialized = True
                    tool_names = ', '.join(self.tools.keys()) if self.tools else 'none'
                    print(f"✓ Connected to MCP server: {self.server_name}")
                    print(f"  Available tools: {tool_names}")
        except Exception as e:
            print(f"✗ Failed to connect to MCP server {self.server_name}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self._initialized or not self.session:
            await self.connect()
        
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            return {
                'success': True,
                'content': result.content,
                'isError': result.isError if hasattr(result, 'isError') else False
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_tools(self) -> Dict[str, Any]:
        """Get list of available tools."""
        return self.tools
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict]:
        """Get schema for a specific tool."""
        if tool_name in self.tools:
            tool = self.tools[tool_name]
            return {
                'name': tool.name,
                'description': tool.description,
                'inputSchema': tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            }
        return None


class MCPToolAdapter:
    """
    Adapter to convert MCP tools to LangGraph-compatible tools.
    
    This allows MCP tools to be used seamlessly in the LangGraph agent.
    """
    
    def __init__(self, mcp_client: MCPClient):
        """
        Initialize the adapter.
        
        Args:
            mcp_client: MCP client instance
        """
        self.mcp_client = mcp_client
        self._langchain_tools = None
    
    async def initialize(self):
        """Initialize the MCP client and create LangChain tools."""
        await self.mcp_client.connect()
        self._create_langchain_tools()
    
    def _create_langchain_tools(self):
        """Create LangChain-compatible tools from MCP tools."""
        from langchain_core.tools import Tool
        
        tools = []
        mcp_tools = self.mcp_client.get_tools()
        
        for tool_name, tool_info in mcp_tools.items():
            # Create a LangChain tool wrapper
            async def make_tool_func(name: str):
                async def tool_func(**kwargs):
                    result = await self.mcp_client.call_tool(name, kwargs)
                    if result['success']:
                        # Extract text content from result
                        if isinstance(result.get('content'), list):
                            content = result['content'][0].text if result['content'] else ""
                        else:
                            content = str(result.get('content', ''))
                        return content
                    else:
                        raise Exception(result.get('error', 'Unknown error'))
                return tool_func
            
            # Create LangChain tool
            langchain_tool = Tool(
                name=tool_name,
                description=tool_info.description if hasattr(tool_info, 'description') else f"MCP tool: {tool_name}",
                func=lambda **kwargs: asyncio.run(make_tool_func(tool_name)(**kwargs))
            )
            tools.append(langchain_tool)
        
        self._langchain_tools = tools
    
    def get_langchain_tools(self) -> List:
        """Get LangChain-compatible tools."""
        return self._langchain_tools or []


class MCPClientManager:
    """
    Manager for multiple MCP clients.
    
    This manages connections to multiple MCP servers (e.g., Jira, Confluence).
    """
    
    def __init__(self):
        """Initialize the manager."""
        self.clients: Dict[str, MCPClient] = {}
        self.adapters: Dict[str, MCPToolAdapter] = {}
    
    def add_server(self, name: str, command: List[str], env: Optional[Dict] = None):
        """
        Add an MCP server to the manager.
        
        Args:
            name: Server name
            command: Command to start the server
            env: Environment variables
        """
        client = MCPClient(name, command, env)
        adapter = MCPToolAdapter(client)
        self.clients[name] = client
        self.adapters[name] = adapter
    
    async def initialize_all(self):
        """Initialize all MCP servers."""
        for name, adapter in self.adapters.items():
            try:
                await adapter.initialize()
            except Exception as e:
                print(f"⚠ Failed to initialize MCP server '{name}': {e}")
    
    def get_all_tools(self) -> List:
        """Get all tools from all MCP servers."""
        all_tools = []
        for adapter in self.adapters.values():
            all_tools.extend(adapter.get_langchain_tools())
        return all_tools
    
    def get_tools_by_server(self, server_name: str) -> List:
        """Get tools from a specific server."""
        if server_name in self.adapters:
            return self.adapters[server_name].get_langchain_tools()
        return []


def create_jira_mcp_client() -> Optional[MCPClient]:
    """
    Create MCP client for Jira server.
    
    Uses the official Jira MCP server if available.
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check if Jira MCP server is available
    # Common Jira MCP server: @modelcontextprotocol/server-jira
    try:
        # Try to use npx to run the MCP server
        # Note: The actual MCP server package name may vary
        # If this doesn't work, the chatbot will fall back to custom tools
        import platform
        if platform.system() == 'Windows':
            command = ['npx.cmd', '-y', '@modelcontextprotocol/server-jira']
        else:
            command = ['npx', '-y', '@modelcontextprotocol/server-jira']
        
        env = {
            'JIRA_URL': Config.JIRA_URL,
            'JIRA_EMAIL': Config.JIRA_EMAIL,
            'JIRA_API_TOKEN': Config.JIRA_API_TOKEN,
            'JIRA_PROJECT_KEY': Config.JIRA_PROJECT_KEY
        }
        
        # Only create if credentials are configured
        if (Config.JIRA_URL and not Config.JIRA_URL.startswith('https://yourcompany') and
            Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
            Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'):
            return MCPClient('jira', command, env)
        else:
            print("⚠ Jira credentials not configured, skipping Jira MCP server")
            return None
    except Exception as e:
        print(f"⚠ Could not create Jira MCP client: {e}")
        return None


def create_confluence_mcp_client() -> Optional[MCPClient]:
    """
    Create MCP client for Confluence server.
    
    Uses the official Confluence MCP server if available.
    """
    if not MCP_AVAILABLE:
        return None
    
    try:
        # Try to use npx to run the MCP server
        # Note: The actual MCP server package name may vary
        # If this doesn't work, the chatbot will fall back to custom tools
        import platform
        if platform.system() == 'Windows':
            command = ['npx.cmd', '-y', '@modelcontextprotocol/server-confluence']
        else:
            command = ['npx', '-y', '@modelcontextprotocol/server-confluence']
        
        env = {
            'CONFLUENCE_URL': Config.CONFLUENCE_URL,
            'CONFLUENCE_EMAIL': Config.JIRA_EMAIL,  # Same as Jira
            'CONFLUENCE_API_TOKEN': Config.JIRA_API_TOKEN,  # Same as Jira
            'CONFLUENCE_SPACE_KEY': Config.CONFLUENCE_SPACE_KEY
        }
        
        # Only create if credentials are configured
        if (Config.CONFLUENCE_URL and not Config.CONFLUENCE_URL.startswith('https://yourcompany') and
            Config.CONFLUENCE_SPACE_KEY and Config.CONFLUENCE_SPACE_KEY != 'SPACE' and
            Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
            Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'):
            return MCPClient('confluence', command, env)
        else:
            print("⚠ Confluence credentials not configured, skipping Confluence MCP server")
            return None
    except Exception as e:
        print(f"⚠ Could not create Confluence MCP client: {e}")
        return None

