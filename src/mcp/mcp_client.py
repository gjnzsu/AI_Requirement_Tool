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

from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('chatbot.mcp.client')

if not MCP_AVAILABLE:
    logger.warning("MCP SDK not installed. Install with: pip install mcp")


class MCPClient:
    """
    MCP Client for connecting to MCP servers.
    
    This client connects to MCP servers and provides access to their tools.
    Note: MCP connections are managed per-call to handle stdio properly.
    """
    
    def __init__(self, server_name: str, command: List[str], env: Optional[Dict] = None):
        """
        Initialize MCP client.
        
        Args:
            server_name: Name of the MCP server
            command: Command to start the MCP server (e.g., ['npx', '-y', 'mcp-jira'])
            env: Environment variables for the server
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP SDK not installed. Install with: pip install mcp")
        
        self.server_name = server_name
        self.command = command
        self.env = env or {}
        self.tools: Dict[str, Any] = {}
        self._initialized = False
        self._server_params = None
        self._cached_tools: Dict[str, Any] = {}
    
    def _get_server_params(self):
        """Get or create server parameters."""
        if self._server_params is None:
            import platform
            import os
            
            command_exec = self.command[0]
            if platform.system() == 'Windows' and command_exec == 'npx':
                command_exec = 'npx.cmd'
            
            # Merge environment variables with system environment
            merged_env = os.environ.copy()
            merged_env.update(self.env)
            
            self._server_params = StdioServerParameters(
                command=command_exec,
                args=self.command[1:] if len(self.command) > 1 else [],
                env=merged_env
            )
        return self._server_params
    
    async def connect(self):
        """Connect to the MCP server and discover tools."""
        if self._initialized:
            return
        
        # First, verify the command can be executed
        import subprocess
        import platform
        is_windows = platform.system() == 'Windows'
        
        # Test if the command exists and can be run
        test_command = self.command[:2] if len(self.command) >= 2 else self.command
        if test_command[0] in ['npx', 'npx.cmd']:
            # Test npx availability
            try:
                result = subprocess.run(
                    [test_command[0], '--version'],
                    capture_output=True,
                    timeout=5,
                    text=True,
                    shell=is_windows
                )
                if result.returncode != 0:
                    raise Exception(f"npx not available: {result.stderr}")
            except FileNotFoundError:
                raise Exception(f"npx not found. Please install Node.js from https://nodejs.org/")
            except subprocess.TimeoutExpired:
                raise Exception("npx command timed out")
        
        # Check if the package exists (for npx -y commands)
        if len(self.command) > 2 and self.command[1] == '-y':
            package_name = self.command[2]
            # Try to check if package exists (this is best-effort)
            try:
                check_cmd = [test_command[0], 'view', package_name, '--json']
                result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    timeout=5,
                    text=True,
                    shell=is_windows
                )
                if result.returncode != 0 and '404' in result.stderr:
                    logger.warning(f"Package '{package_name}' may not exist in npm registry")
                    logger.debug(f"Error: {result.stderr.strip()}")
            except Exception:
                # Ignore check errors - package might still work
                pass
        
        try:
            server_params = self._get_server_params()
            
            # Create stdio client and connect with timeout
            try:
                # Use a longer timeout for initial connection
                # Try using asyncio.timeout for Python 3.11+, fallback to wait_for for older versions
                try:
                    timeout_context = asyncio.timeout(20.0)
                except AttributeError:
                    # Python < 3.11, use wait_for wrapper
                    timeout_context = None
                
                # Common connection logic
                async def _connect_and_discover():
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(read, write) as session:
                            # Initialize the session with longer timeout
                            try:
                                await asyncio.wait_for(session.initialize(), timeout=15.0)
                            except asyncio.TimeoutError:
                                raise Exception(
                                    f"Server initialization timeout. "
                                    f"The MCP server '{self.server_name}' may not be responding. "
                                    f"Check if the package is installed: npm install -g {self.command[-1] if len(self.command) > 1 else 'package-name'}"
                                )
                            
                            # List available tools
                            try:
                                tools_result = await asyncio.wait_for(session.list_tools(), timeout=10.0)
                                
                                # Handle different response formats
                                if hasattr(tools_result, 'tools'):
                                    tools_list = tools_result.tools
                                elif isinstance(tools_result, list):
                                    tools_list = tools_result
                                elif hasattr(tools_result, '__iter__'):
                                    tools_list = list(tools_result)
                                else:
                                    tools_list = getattr(tools_result, 'tools', [])
                                
                                # Cache tool schemas
                                self._cached_tools = {}
                                for tool in tools_list:
                                    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                                    self._cached_tools[tool_name] = {
                                        'name': tool_name,
                                        'description': getattr(tool, 'description', f'MCP tool: {tool_name}'),
                                        'inputSchema': getattr(tool, 'inputSchema', {})
                                    }
                                
                                self.tools = {name: info for name, info in self._cached_tools.items()}
                                
                            except asyncio.TimeoutError:
                                logger.warning(f"Timeout listing tools from {self.server_name}")
                                self.tools = {}
                            except Exception as e:
                                logger.warning(f"Could not list tools from {self.server_name}: {e}")
                                self.tools = {}
                            
                            self._initialized = True
                            tool_names = ', '.join(self.tools.keys()) if self.tools else 'none'
                            logger.info(f"Connected to MCP server: {self.server_name}")
                            logger.debug(f"Available tools: {tool_names}")
                
                # Execute with appropriate timeout mechanism
                if timeout_context:
                    async with timeout_context:
                        await _connect_and_discover()
                else:
                    # Fallback for older Python versions
                    await asyncio.wait_for(_connect_and_discover(), timeout=20.0)
                
                return
            except asyncio.TimeoutError:
                raise Exception(
                    f"Connection timeout to {self.server_name} MCP server. "
                    f"The server may not be installed or may require additional setup. "
                    f"Command: {' '.join(self.command)}"
                )
            except FileNotFoundError:
                package_name = self.command[-1] if len(self.command) > 1 else 'unknown'
                raise Exception(
                    f"MCP server package '{package_name}' not found. "
                    f"Install with: npm install -g {package_name}"
                )
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if "not found" in error_msg.lower() or "cannot find" in error_msg.lower():
                package_name = self.command[-1] if len(self.command) > 1 else 'unknown'
                logger.error(f"MCP server package '{package_name}' not available")
                logger.info(f"Try installing: npm install -g {package_name}")
            elif "timeout" in error_msg.lower():
                logger.error(f"Failed to connect to MCP server {self.server_name}: {error_msg}")
                logger.info("This may indicate:")
                logger.info("  - The package is not installed")
                logger.info("  - The server requires additional configuration")
                logger.info("  - Network connectivity issues")
            else:
                logger.error(f"Failed to connect to MCP server {self.server_name}: {error_msg}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.
        
        Note: Each call creates a new connection since MCP stdio connections
        are managed per-session. Tools are cached from initial discovery.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self._initialized:
            await self.connect()
        
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}")
        
        try:
            server_params = self._get_server_params()
            
            # Create a new connection for this tool call
            # MCP stdio connections are session-based
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    # Increase timeout for Jira operations (they can take longer)
                    result = await asyncio.wait_for(
                        session.call_tool(tool_name, arguments),
                        timeout=60.0  # Increased from 30 to 60 seconds
                    )
                    return {
                        'success': True,
                        'content': result.content,
                        'isError': result.isError if hasattr(result, 'isError') else False
                    }
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f'Tool call timeout for {tool_name}'
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
        """Initialize all MCP servers with individual timeouts."""
        for name, adapter in self.adapters.items():
            try:
                # Add individual timeout for each server (15 seconds)
                await asyncio.wait_for(adapter.initialize(), timeout=15.0)
            except asyncio.TimeoutError:
                logger.warning(f"MCP server '{name}' initialization timeout (15s), skipping")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP server '{name}': {e}")
    
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


def create_rovo_mcp_client() -> Optional[MCPClient]:
    """
    Create MCP client for Atlassian Rovo MCP Server (Official).
    
    The Atlassian Rovo MCP Server is Atlassian's official cloud-based MCP server.
    It uses OAuth 2.1 authentication and connects via mcp-remote proxy.
    
    Documentation: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check if mcp-remote is available (required for Rovo)
    import shutil
    import platform
    is_windows = platform.system() == 'Windows'
    npx_cmd = 'npx.cmd' if is_windows else 'npx'
    
    # Check if npx is available
    if not shutil.which(npx_cmd):
        return None
    
    try:
        # Use mcp-remote to connect to Atlassian Rovo MCP Server
        # The server endpoint is: https://mcp.atlassian.com/v1/sse
        # mcp-remote acts as a proxy between local stdio and remote SSE
        command = [
            npx_cmd, '-y', 'mcp-remote',
            'https://mcp.atlassian.com/v1/sse'
        ]
        
        # Rovo uses OAuth 2.1, so we don't need API tokens in env
        # The OAuth flow will be handled by mcp-remote
        env = {
            # Optional: Can specify Atlassian site URL if needed
            # 'ATLASSIAN_SITE_URL': Config.JIRA_URL,
        }
        
        client = MCPClient('atlassian-rovo', command, env)
        logger.info("Created Atlassian Rovo MCP client (Official)")
        logger.info("Note: OAuth 2.1 authentication will be required on first use")
        return client
    except Exception as e:
        # mcp-remote might not be available or Rovo might not be accessible
        return None


def create_custom_jira_mcp_client() -> Optional[MCPClient]:
    """
    Create MCP client for custom Python-based Jira MCP server.
    
    This uses our own Jira MCP server implementation.
    """
    if not MCP_AVAILABLE:
        return None
    
    # Check if credentials are configured
    if not (Config.JIRA_URL and not Config.JIRA_URL.startswith('https://yourcompany') and
            Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
            Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'):
        return None
    
    try:
        import platform
        import sys
        is_windows = platform.system() == 'Windows'
        
        # Use Python to run our custom MCP server
        python_exe = sys.executable
        server_script = str(Path(__file__).parent / 'jira_mcp_server.py')
        
        command = [python_exe, server_script]
        
        env = {
            'JIRA_URL': Config.JIRA_URL,
            'JIRA_EMAIL': Config.JIRA_EMAIL,
            'JIRA_API_TOKEN': Config.JIRA_API_TOKEN,
            'JIRA_PROJECT_KEY': Config.JIRA_PROJECT_KEY
        }
        
        client = MCPClient('custom-jira', command, env)
        logger.info("Created custom Jira MCP client (Python-based)")
        return client
    except Exception as e:
        logger.warning(f"Could not create custom Jira MCP client: {e}")
        return None


def create_jira_mcp_client() -> Optional[MCPClient]:
    """
    Create MCP client for Jira server.
    
    Only uses the custom Python-based Jira MCP Server.
    Atlassian Rovo MCP Server is disabled.
    """
    if not MCP_AVAILABLE:
        return None
    
    # Only use custom Python-based MCP server
    custom_client = create_custom_jira_mcp_client()
    if custom_client:
        return custom_client
    
    # No fallback to Rovo or other servers
    # Will fall back to custom tools automatically
    return None


def create_confluence_mcp_client() -> Optional[MCPClient]:
    """
    Create MCP client for Confluence server.
    
    Tries official Atlassian Rovo MCP Server first, then falls back to community packages.
    """
    if not MCP_AVAILABLE:
        return None
    
    import platform
    is_windows = platform.system() == 'Windows'
    npx_cmd = 'npx.cmd' if is_windows else 'npx'
    
    # First, try official Atlassian Rovo MCP Server
    rovo_client = create_rovo_mcp_client()
    if rovo_client:
        # Rename to 'confluence' for consistency
        rovo_client.server_name = 'confluence'
        logger.info("Using official Atlassian Rovo MCP Server for Confluence")
        return rovo_client
    
    # Fallback to community packages if credentials are configured
    if not (Config.CONFLUENCE_URL and not Config.CONFLUENCE_URL.startswith('https://yourcompany') and
            Config.CONFLUENCE_SPACE_KEY and Config.CONFLUENCE_SPACE_KEY != 'SPACE' and
            Config.JIRA_EMAIL and Config.JIRA_EMAIL != 'your-email@example.com' and
            Config.JIRA_API_TOKEN and Config.JIRA_API_TOKEN != 'your-api-token'):
        logger.warning("Confluence credentials not configured, skipping Confluence MCP server")
        return None
    
    # Try community MCP server packages
    mcp_server_options = [
        {
            'name': 'mcp-atlassian',
            'package': 'mcp-atlassian',
            'env': {
                'CONFLUENCE_URL': Config.CONFLUENCE_URL,
                'CONFLUENCE_EMAIL': Config.JIRA_EMAIL,
                'CONFLUENCE_API_TOKEN': Config.JIRA_API_TOKEN,
                'CONFLUENCE_SPACE_KEY': Config.CONFLUENCE_SPACE_KEY,
                'ATLASSIAN_URL': Config.CONFLUENCE_URL,  # Some servers use ATLASSIAN_URL
            }
        },
        {
            'name': '@modelcontextprotocol/server-confluence',
            'package': '@modelcontextprotocol/server-confluence',
            'env': {
                'CONFLUENCE_URL': Config.CONFLUENCE_URL,
                'CONFLUENCE_EMAIL': Config.JIRA_EMAIL,
                'CONFLUENCE_API_TOKEN': Config.JIRA_API_TOKEN,
                'CONFLUENCE_SPACE_KEY': Config.CONFLUENCE_SPACE_KEY
            }
        }
    ]
    
    # Try each option
    for option in mcp_server_options:
        try:
            command = [npx_cmd, '-y', option['package']]
            client = MCPClient('confluence', command, option['env'])
            logger.info(f"Created Confluence MCP client using {option['name']}")
            return client
        except Exception as e:
            # Try next option
            continue
    
    # If all options failed, return None (will fall back to custom tools)
    logger.warning("Could not create Confluence MCP client")
    logger.info("Using custom tools as fallback")
    return None

