# Custom Jira MCP Server

## Overview

We've built a **custom Python-based Jira MCP server** that wraps our existing JiraTool functionality and exposes it via the Model Context Protocol (MCP). This provides a more reliable and controllable solution compared to external MCP servers.

## Why Build Our Own?

1. **Reliability**: No dependency on external services that may be unstable
2. **Control**: Full control over functionality and error handling
3. **Integration**: Uses our existing, tested JiraTool code
4. **Performance**: Direct Python execution, no Node.js/npm dependencies
5. **Customization**: Easy to extend with additional features

## Architecture

```
User Request
    ↓
LangGraph Agent
    ↓
MCP Integration
    ↓
Custom Jira MCP Server (Python)
    ↓
JiraTool (Existing Implementation)
    ↓
Jira REST API
```

## Features

The custom Jira MCP server provides a single, focused tool:

### `create_jira_issue`
Create a new Jira issue and return the ticket ID.

**Parameters:**
- `summary` (required): Issue summary/title
- `description` (required): Issue description
- `priority` (optional): High, Medium, Low (default: Medium)
- `issue_type` (optional): Story, Task, Bug, Epic (default: Story)

**Returns:**
```json
{
  "success": true,
  "ticket_id": "PROJ-123",
  "issue_key": "PROJ-123",
  "link": "https://yourcompany.atlassian.net/browse/PROJ-123"
}
```

**Example:**
```json
{
  "summary": "Implement user authentication",
  "description": "Add login and registration functionality",
  "priority": "High",
  "issue_type": "Story"
}
```

## Installation

### Prerequisites

1. **Python MCP SDK** (already installed if you have `mcp` package):
   ```powershell
   pip install mcp
   ```

2. **Jira Credentials** (configured in `.env`):
   ```env
   JIRA_URL=https://yourcompany.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-api-token
   JIRA_PROJECT_KEY=PROJ
   ```

### No Additional Installation Needed!

The custom MCP server is part of the codebase and runs directly with Python. No Node.js, npm, or external packages required!

## How It Works

### Server Startup

The custom Jira MCP server:
1. Initializes Jira connection using existing JiraTool
2. Registers MCP tools
3. Runs as a stdio-based MCP server
4. Accepts tool calls via MCP protocol

### Client Connection

The MCP client:
1. Spawns Python process running `jira_mcp_server.py`
2. Connects via stdio (standard input/output)
3. Discovers available tools
4. Executes tool calls

## Integration

The custom server is automatically used as the **first priority** in the MCP client fallback chain:

1. ✅ **Custom Python MCP Server** (Recommended - Most Reliable)
2. Atlassian Rovo MCP Server (Official)
3. mcp-jira (Community)
4. mcp-atlassian (Community)
5. Custom Tools (Always available)

## Testing

Test the custom Jira MCP server:

```powershell
python test_custom_jira_mcp.py
```

This will:
- Verify Jira credentials
- Create MCP client
- Connect to server
- List available tools
- Test a tool call

## Usage

The custom server is used automatically when:
- MCP is enabled (`USE_MCP=true`)
- Jira credentials are configured
- The server script is accessible

No manual configuration needed!

## Advantages Over External Servers

| Feature | Custom Server | External Servers |
|---------|---------------|------------------|
| Reliability | ✅ High (our code) | ⚠️ Variable |
| Control | ✅ Full | ❌ Limited |
| Dependencies | ✅ Python only | ⚠️ Node.js/npm |
| Customization | ✅ Easy | ❌ Difficult |
| Debugging | ✅ Easy | ❌ Hard |
| Performance | ✅ Direct | ⚠️ Process overhead |

## Design Philosophy

This is a **simplified, focused MCP server** that does one thing well:
- ✅ Create Jira issues
- ✅ Return ticket ID
- ✅ Simple and reliable

For other Jira operations (search, update, etc.), use the existing custom tools directly.

## Troubleshooting

### Server Won't Start

**Error**: `MCP server SDK not available`

**Solution**:
```powershell
pip install mcp
```

### Connection Timeout

**Error**: `Connection timeout`

**Possible Causes**:
1. Jira credentials not configured
2. Network connectivity issues
3. Jira API rate limiting

**Solution**:
- Check `.env` file has correct credentials
- Verify network connectivity
- Check Jira API status

### Tool Call Fails

**Error**: `Tool call failed`

**Check**:
1. Jira credentials are valid
2. User has permissions for the operation
3. Issue key/project key exists

## Summary

✅ **Custom Jira MCP Server**: Built and ready to use  
✅ **No External Dependencies**: Runs with Python only  
✅ **Reliable**: Uses tested JiraTool code  
✅ **Extensible**: Easy to add new features  
✅ **Automatic**: Integrated into MCP client fallback chain  

The custom Jira MCP server provides a stable, reliable solution for Jira integration via MCP protocol!

