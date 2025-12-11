"""
MCP Integration for LangGraph Agent.

This module integrates MCP tools into the LangGraph agent.
"""

import asyncio
import sys
from typing import List, Optional, Dict, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('chatbot.mcp')

try:
    from .mcp_client import MCPClientManager, create_jira_mcp_client, create_confluence_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP client not available. Install MCP SDK: pip install mcp")


class MCPToolWrapper(StructuredTool):
    """
    Wrapper to make MCP tools compatible with LangChain/LangGraph.
    Uses StructuredTool to properly handle multiple parameters.
    """
    
    # Use model_config to allow extra attributes and ignore unknown fields
    model_config = {"extra": "allow", "arbitrary_types_allowed": True}
    
    def __init__(self, mcp_client, tool_name: str, tool_schema: Dict):
        """
        Initialize MCP tool wrapper.
        
        Args:
            mcp_client: MCP client instance
            tool_name: Name of the tool
            tool_schema: Tool schema from MCP
        """
        # Verify client before proceeding
        if mcp_client is None:
            raise ValueError(f"MCPToolWrapper: mcp_client is None for tool '{tool_name}'")
        if not hasattr(mcp_client, 'call_tool'):
            raise ValueError(f"MCPToolWrapper: client does not have 'call_tool' method. Client type: {type(mcp_client)}")
        
        # Capture client and tool_name in closure to ensure they persist
        # even if Pydantic resets instance attributes
        captured_client = mcp_client
        captured_tool_name = tool_name
        
        # Extract description and parameters
        description = tool_schema.get('description', f'MCP tool: {tool_name}')
        name = tool_schema.get('name', tool_name)
        input_schema = tool_schema.get('inputSchema', {})
        
        # Create a dynamic Pydantic model from the input schema
        def _create_args_schema():
            """Create a dynamic Pydantic model from input schema."""
            from pydantic import create_model
            
            # Get properties from input schema
            properties = input_schema.get('properties', {})
            required = input_schema.get('required', [])
            
            # Create field definitions for create_model
            field_definitions = {}
            for prop_name, prop_info in properties.items():
                # Determine Python type
                prop_type = str  # Default to str
                if prop_info.get('type') == 'string':
                    prop_type = str
                elif prop_info.get('type') == 'integer':
                    prop_type = int
                elif prop_info.get('type') == 'boolean':
                    prop_type = bool
                elif prop_info.get('type') == 'number':
                    prop_type = float
                
                # Determine default value
                if prop_name in required:
                    default = ...
                else:
                    default = None
                    from typing import Optional
                    prop_type = Optional[prop_type]
                
                # Create Field with description
                field_definitions[prop_name] = (
                    prop_type,
                    Field(
                        default=default,
                        description=prop_info.get('description', '')
                    )
                )
            
            # Use create_model for Pydantic v2
            if field_definitions:
                return create_model('ArgsSchema', **field_definitions)
            else:
                return None
        
        args_schema = _create_args_schema() if input_schema else None
        
        # Create wrapper functions that capture the client in closure
        def _run_sync_wrapper(**kwargs) -> str:
            """Synchronous execution wrapper with captured client."""
            return asyncio.run(_arun_wrapper(**kwargs))
        
        async def _arun_wrapper(**kwargs) -> str:
            """Asynchronous execution with captured client."""
            try:
                # Add timeout for MCP tool calls (60 seconds for Jira operations)
                result = await asyncio.wait_for(
                    captured_client.call_tool(captured_tool_name, kwargs),
                    timeout=60.0
                )
                
                # Check both success flag and isError flag
                is_error = result.get('isError', False)
                success = result.get('success', False)
                
                if success and not is_error:
                    # Extract text content
                    content = result.get('content', [])
                    
                    # Handle different content formats
                    text = None
                    
                    if isinstance(content, list) and len(content) > 0:
                        first_item = content[0]
                        
                        # Try different ways to extract text
                        if hasattr(first_item, 'text'):
                            text = first_item.text
                        elif isinstance(first_item, dict):
                            text = first_item.get('text', str(first_item))
                        else:
                            text = str(first_item)
                    elif isinstance(content, str):
                        text = content
                    else:
                        text = str(content) if content else "Success"
                    
                    return text if text else "Success"
                else:
                    # Handle error case
                    error_msg = result.get('error', 'Unknown error')
                    if is_error:
                        # If isError is True, try to extract error from content
                        content = result.get('content', [])
                        if isinstance(content, list) and len(content) > 0:
                            first_item = content[0]
                            if isinstance(first_item, dict):
                                error_detail = first_item.get('text', str(first_item))
                                error_msg = f"Error: {error_detail}"
                            else:
                                error_msg = f"Error: {str(first_item)}"
                        elif isinstance(content, str):
                            error_msg = f"Error: {content}"
                    
                    return f"Error: {error_msg}" if not error_msg.startswith('Error:') else error_msg
            except asyncio.TimeoutError:
                return f"Error: Tool '{captured_tool_name}' execution timed out after 60 seconds. The MCP server may be slow or unresponsive."
            except Exception as e:
                error_msg = f"Error executing tool: {str(e)}"
                logger.error(f"MCP tool error: {e}", exc_info=True)
                return error_msg
        
        # Call super().__init__ with the wrapper function
        super().__init__(
            name=name,
            description=description,
            args_schema=args_schema,
            func=_run_sync_wrapper
        )
        
        # Store as instance attributes using object.__setattr__ to bypass Pydantic
        # This ensures they persist even if Pydantic tries to reset them
        object.__setattr__(self, '_mcp_client', mcp_client)
        object.__setattr__(self, '_tool_name', tool_name)
        object.__setattr__(self, '_tool_schema', tool_schema)


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
        """Initialize MCP clients and load tools with timeout."""
        if not self.use_mcp:
            return
        
        # Note: Custom Python-based MCP server doesn't require Node.js/npx
        # Only community Node.js-based servers would need it
        
        try:
            # Add overall timeout for MCP initialization (30 seconds)
            await asyncio.wait_for(self._initialize_mcp_servers(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("MCP initialization timeout (30s)")
            logger.info("Falling back to custom tools")
            self.use_mcp = False
            self._initialized = False
        except Exception as e:
            logger.warning(f"MCP Integration failed: {e}")
            logger.info("Falling back to custom tools")
            self.use_mcp = False
            self._initialized = False
            logger.debug("MCP initialization error details", exc_info=True)
    
    async def _initialize_mcp_servers(self):
        """Internal method to initialize MCP servers."""
        self.manager = MCPClientManager()
        
        # Add Jira MCP server (custom Python-based only)
        jira_client = create_jira_mcp_client()
        if jira_client:
            self.manager.add_server('jira', jira_client.command, jira_client.env)
            logger.info("Using custom Jira MCP server (Python-based)")
        
        # Add Confluence MCP server (official Atlassian Rovo or community packages)
        confluence_client = create_confluence_mcp_client()
        if confluence_client:
            self.manager.add_server('confluence', confluence_client.command, confluence_client.env)
            logger.info("Confluence MCP server added")
        
        # Initialize all servers (each with individual timeout handled in manager)
        await self.manager.initialize_all()
        
        # Create tools using MCPToolWrapper (StructuredTool) instead of adapter's simple tools
        self.tools = []
        for server_name, client in self.manager.clients.items():
            if client._initialized:
                tools_dict = client.get_tools()
                for tool_name, tool_info in tools_dict.items():
                    # Verify client is valid
                    if client is None:
                        continue
                    
                    # Create MCPToolWrapper which uses StructuredTool
                    try:
                        tool_wrapper = MCPToolWrapper(
                            mcp_client=client,
                            tool_name=tool_name,
                            tool_schema={
                                'name': tool_name,
                                'description': tool_info.get('description', f'MCP tool: {tool_name}'),
                                'inputSchema': tool_info.get('inputSchema', {})
                            }
                        )
                        self.tools.append(tool_wrapper)
                    except Exception as e:
                        logger.error(f"Failed to create MCPToolWrapper for '{tool_name}': {e}", exc_info=True)
        
        if self.tools:
            self._initialized = True
            logger.info(f"MCP Integration initialized with {len(self.tools)} tools")
        else:
            logger.warning("MCP servers initialized but no tools available")
            logger.info("Falling back to custom tools")
            self.use_mcp = False
    
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
            logger.warning(f"npx check failed: {e}")
            return False
    
    def get_tools(self) -> List[BaseTool]:
        """Get available MCP tools."""
        # Don't auto-initialize here - initialization should be explicit
        # This prevents blocking on first request (e.g., general chat)
        # Return empty list if not initialized rather than blocking
        if not self._initialized:
            return []
        
        return self.tools
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        # Don't auto-initialize - return False if not initialized
        if not self._initialized:
            return False
        return any(tool.name == tool_name for tool in self.tools)
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a specific tool by name."""
        # Don't auto-initialize - return None if not initialized
        if not self._initialized:
            return None
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None
    
    async def check_confluence_mcp_health(self) -> Dict[str, Any]:
        """
        Check health/readiness of Confluence MCP server.
        
        Returns:
            Dictionary with health status information
        """
        if not self.use_mcp or not MCP_AVAILABLE:
            return {
                'healthy': False,
                'reason': 'MCP not enabled or not available',
                'confluence_tools_available': False
            }
        
        if not self.manager:
            return {
                'healthy': False,
                'reason': 'MCP manager not initialized',
                'confluence_tools_available': False
            }
        
        # Check if Confluence client exists
        confluence_client = self.manager.clients.get('confluence')
        if not confluence_client:
            return {
                'healthy': False,
                'reason': 'Confluence MCP client not found',
                'confluence_tools_available': False
            }
        
        # Check if client is initialized
        if not confluence_client._initialized:
            try:
                await confluence_client.connect()
            except Exception as e:
                return {
                    'healthy': False,
                    'reason': f'Failed to initialize Confluence MCP client: {str(e)}',
                    'confluence_tools_available': False
                }
        
        # Check available tools
        confluence_tools = confluence_client.get_tools()
        confluence_tool_names = list(confluence_tools.keys()) if confluence_tools else []
        
        # Check for common Confluence tool names
        has_create_tool = any('create' in name.lower() and 'page' in name.lower() 
                             for name in confluence_tool_names)
        has_get_tool = any('get' in name.lower() or 'read' in name.lower() 
                          for name in confluence_tool_names)
        
        return {
            'healthy': True,
            'reason': 'Confluence MCP server is ready',
            'confluence_tools_available': True,
            'confluence_tool_count': len(confluence_tool_names),
            'confluence_tool_names': confluence_tool_names,
            'has_create_page_tool': has_create_tool,
            'has_get_page_tool': has_get_tool,
            'server_name': confluence_client.server_name
        }

