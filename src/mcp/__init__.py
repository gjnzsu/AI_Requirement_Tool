"""
MCP (Model Context Protocol) Client Integration.

This module provides MCP client functionality to connect to MCP servers
and use their tools in the chatbot.
"""

from .mcp_client import MCPClient, MCPToolAdapter

__all__ = ['MCPClient', 'MCPToolAdapter']

