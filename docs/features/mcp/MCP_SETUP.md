# MCP (Model Context Protocol) Setup Guide

## Overview

The chatbot now supports **actual MCP protocol** integration! This allows you to use existing MCP servers for Jira and Confluence instead of custom tools.

## What is MCP?

MCP (Model Context Protocol) is an open standard that enables AI assistants to securely access external tools and data sources. By using MCP, you can:

- ✅ Use standardized, community-maintained MCP servers
- ✅ Easily add new tools from the MCP ecosystem
- ✅ Better interoperability with other MCP-compatible systems

## Prerequisites

### 1. Install MCP SDK

```powershell
pip install mcp
```

### 2. Install Node.js (for MCP servers)

MCP servers are typically Node.js packages. Install Node.js if you haven't:
- Download from: https://nodejs.org/
- Or use: `winget install OpenJS.NodeJS`

### 3. Install MCP Servers

Install the official Jira and Confluence MCP servers:

```powershell
# Jira MCP Server
npx -y @modelcontextprotocol/server-jira

# Confluence MCP Server  
npx -y @modelcontextprotocol/server-confluence
```

**Note:** These will be installed automatically when first used via `npx`.

## Configuration

### Option 1: Use MCP Servers (Recommended)

The chatbot will automatically try to use MCP servers if available. No additional configuration needed if you have:

1. ✅ MCP SDK installed (`pip install mcp`)
2. ✅ Node.js installed
3. ✅ Jira/Confluence credentials in `.env`

The MCP servers will use the same credentials from your `.env` file:
- `JIRA_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`
- `CONFLUENCE_URL`
- `CONFLUENCE_SPACE_KEY`

### Option 2: Fallback to Custom Tools

If MCP is not available or fails, the chatbot automatically falls back to custom tools. No action needed.

## How It Works

### Architecture

```
Chatbot (LangGraph Agent)
    ↓
MCP Client Manager
    ├─→ Jira MCP Server (via npx)
    └─→ Confluence MCP Server (via npx)
```

### Flow

1. **Agent Initialization**: Tries to connect to MCP servers
2. **Tool Discovery**: Automatically discovers available tools from MCP servers
3. **Tool Execution**: Uses MCP tools when available, falls back to custom tools if not

## Verification

### Check MCP Integration

When the chatbot starts, you should see:

```
✓ MCP Integration initialized with X tools
  Available tools: create_issue, get_issue, create_page, ...
```

If you see:
```
⚠ MCP not available: ...
   Falling back to custom tools
```

Then MCP is not available, but custom tools will still work.

### Test MCP Tools

```python
from src.agent import ChatbotAgent

agent = ChatbotAgent(use_mcp=True)
# Check if MCP tools are available
if agent.mcp_integration:
    tools = agent.mcp_integration.get_tools()
    print(f"Available MCP tools: {[t.name for t in tools]}")
```

## Troubleshooting

### "MCP SDK not installed"

**Solution:**
```powershell
pip install mcp
```

### "Node.js not found"

**Solution:**
- Install Node.js from https://nodejs.org/
- Or use: `winget install OpenJS.NodeJS`
- Restart your terminal

### "MCP server not found"

**Solution:**
- The MCP servers are installed via `npx` automatically
- Make sure you have internet connection
- Try manually: `npx -y @modelcontextprotocol/server-jira`

### "MCP initialization failed"

**Possible causes:**
- Missing credentials in `.env`
- Network connectivity issues
- MCP server startup errors

**Solution:**
- Check your `.env` file has all required credentials
- Check server logs for specific errors
- The chatbot will automatically fall back to custom tools

### Tools Not Working

If MCP tools don't work:
1. Check MCP integration initialized successfully
2. Verify credentials are correct
3. Check MCP server logs
4. Fall back to custom tools (set `use_mcp=False`)

## Disabling MCP

If you want to use only custom tools:

```python
from src.chatbot import Chatbot

chatbot = Chatbot(
    use_agent=True,
    use_mcp=False  # Disable MCP, use custom tools only
)
```

Or in `.env`:
```env
USE_MCP=false
```

## Available MCP Servers

### Official MCP Servers

- **Jira**: `@modelcontextprotocol/server-jira`
- **Confluence**: `@modelcontextprotocol/server-confluence`

### Community MCP Servers

You can add more MCP servers by:
1. Finding MCP servers on: https://github.com/modelcontextprotocol/servers
2. Adding them to `MCPClientManager` in `src/mcp/mcp_client.py`

## Benefits of MCP

✅ **Standardized**: Uses open protocol standard  
✅ **Extensible**: Easy to add new MCP servers  
✅ **Maintained**: Community-maintained servers  
✅ **Interoperable**: Works with any MCP-compatible client  
✅ **Fallback**: Automatically falls back to custom tools if MCP unavailable  

## Next Steps

1. Install MCP SDK: `pip install mcp`
2. Ensure Node.js is installed
3. Start the chatbot - MCP will be used automatically if available
4. Check logs to verify MCP integration

## See Also

- MCP Documentation: https://modelcontextprotocol.io
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- MCP Servers: https://github.com/modelcontextprotocol/servers

