# MCP Server Configuration

## Current Configuration

### ✅ Enabled: Custom Jira MCP Server

The chatbot now **only uses the custom Python-based Jira MCP server** that we built.

**Location**: `src/mcp/jira_mcp_server.py`

**Features**:
- Single tool: `create_jira_issue`
- Returns ticket ID (e.g., "PROJ-123")
- Python-based (no Node.js/npm required)
- Uses existing JiraTool code
- Reliable and stable

### ❌ Disabled: Atlassian Rovo MCP Server

The Atlassian Rovo MCP Server has been **disabled** due to stability issues.

**Why Disabled**:
- Connection timeouts
- Unstable behavior
- OAuth 2.1 complexity
- Better to use our own reliable solution

## MCP Server Priority

The system now uses this priority order:

1. ✅ **Custom Python Jira MCP Server** (Only option for Jira)
2. Custom Tools (Fallback - always available)

## Configuration

### Enable/Disable MCP

To disable MCP entirely (use custom tools only):

```env
USE_MCP=false
```

### Jira Credentials

Required for custom Jira MCP server:

```env
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ
```

## Testing

Test the custom Jira MCP server:

```powershell
python test_custom_jira_mcp.py
```

Or test the server directly:

```powershell
python src/mcp/jira_mcp_server.py
```

## Benefits

✅ **Reliable**: Uses our own tested code  
✅ **Simple**: Single tool, focused functionality  
✅ **Fast**: Direct Python execution  
✅ **No Dependencies**: No Node.js/npm needed  
✅ **Full Control**: We own the code  

## Summary

- ✅ Custom Jira MCP Server: **Enabled** (only option)
- ❌ Atlassian Rovo MCP Server: **Disabled**
- ✅ Custom Tools: **Always available as fallback**

The chatbot will now use only the custom-built Jira MCP server for reliable Jira issue creation!

