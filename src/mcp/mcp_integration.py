"""
MCP Integration for LangGraph Agent.

This module integrates MCP tools into the LangGraph agent.
"""

import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.tools import BaseTool
from config.config import Config

try:
    from .mcp_client import MCPClientManager, create_jira_mcp_client, create_confluence_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠ MCP client not available. Install MCP SDK: pip install mcp")


class MCPToolWrapper(BaseTool):
    """
    Wrapper to make MCP tools compatible with LangChain/LangGraph.
    """
    
    def __init__(self, mcp_client, tool_name: str, tool_schema: Dict):
        """
        Initialize MCP tool wrapper.
        
        Args:
            mcp_client: MCP client instance
            tool_name: Name of the tool
            tool_schema: Tool schema from MCP
        """
        self.mcp_client = mcp_client
        self.tool_name = tool_name
        self.tool_schema = tool_schema
        
        # Extract description and parameters
        description = tool_schema.get('description', f'MCP tool: {tool_name}')
        name = tool_schema.get('name', tool_name)
        
        super().__init__(name=name, description=description)
    
    def _run(self, **kwargs) -> str:
        """Synchronous execution (wraps async)."""
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs) -> str:
        """Asynchronous execution."""
        try:
            result = await self.mcp_client.call_tool(self.tool_name, kwargs)
            if result['success']:
                # Extract text content
                content = result.get('content', [])
                if isinstance(content, list) and len(content) > 0:
                    if hasattr(content[0], 'text'):
                        return content[0].text
                    elif isinstance(content[0], dict):
                        return content[0].get('text', str(content[0]))
                return str(content) if content else "Success"
            else:
                return f"Error: {result.get('error', 'Unknown error')}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"


class MCPIntegration:
    """
    Integration layer for MCP tools in the agent.
    """
    
    def __init__(self, use_mcp: bool = True):
        """
        Initialize MCP integration.
        
        Args:
            use_mcp: Whether to use MCP (default: True)
        """
        self.use_mcp = use_mcp and MCP_AVAILABLE
        self.manager: Optional[MCPClientManager] = None
        self.tools: List[BaseTool] = []
        self._initialized = False
    
    async def initialize(self):
        """Initialize MCP clients and load tools."""
        if not self.use_mcp:
            return
        
        # Check if Node.js/npx is available
        if not self._check_npx_available():
            print("⚠ Node.js/npx not found. MCP requires Node.js to run MCP servers.")
            print("   Install Node.js from: https://nodejs.org/")
            print("   Falling back to custom tools")
            self.use_mcp = False
            return
        
        try:
            self.manager = MCPClientManager()
            
            # Add Jira MCP server
            jira_client = create_jira_mcp_client()
            if jira_client:
                self.manager.add_server('jira', jira_client.command, jira_client.env)
            
            # Add Confluence MCP server
            confluence_client = create_confluence_mcp_client()
            if confluence_client:
                self.manager.add_server('confluence', confluence_client.command, confluence_client.env)
            
            # Initialize all servers
            await self.manager.initialize_all()
            
            # Get all tools
            self.tools = self.manager.get_all_tools()
            
            if self.tools:
                self._initialized = True
                print(f"✓ MCP Integration initialized with {len(self.tools)} tools")
            else:
                print("⚠ MCP servers initialized but no tools available")
                print("   Falling back to custom tools")
                self.use_mcp = False
        except Exception as e:
            print(f"⚠ MCP Integration failed: {e}")
            print("   Falling back to custom tools")
            self.use_mcp = False
            import traceback
            traceback.print_exc()
    
    def _check_npx_available(self) -> bool:
        """Check if npx is available on the system."""
        import subprocess
        import shutil
        import platform
        
        # Check if npx command exists
        npx_path = shutil.which('npx')
        if not npx_path:
            # On Windows, try with .cmd extension
            if platform.system() == 'Windows':
                npx_path = shutil.which('npx.cmd')
            if not npx_path:
                return False
        
        # Try to run npx --version to verify it works
        try:
            # On Windows, use shell=True to handle PowerShell execution policy
            use_shell = platform.system() == 'Windows'
            result = subprocess.run(
                ['npx', '--version'] if not use_shell else ['npx.cmd', '--version'],
                capture_output=True,
                timeout=5,
                text=True,
                shell=use_shell
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            print(f"⚠ npx check failed: {e}")
            return False
    
    def get_tools(self) -> List[BaseTool]:
        """Get available MCP tools."""
        if not self._initialized:
            # Try to initialize synchronously
            try:
                asyncio.run(self.initialize())
            except Exception as e:
                print(f"⚠ Could not initialize MCP: {e}")
        
        return self.tools
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        return any(tool.name == tool_name for tool in self.tools)
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a specific tool by name."""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

