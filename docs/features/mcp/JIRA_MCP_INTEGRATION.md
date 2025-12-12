# Jira MCP Server Integration

## Overview

The Jira MCP (Model Context Protocol) integration allows the chatbot to interact with Jira through standardized MCP servers. This provides a more flexible and extensible approach compared to direct API integration.

## What's New

### ✅ Updated MCP Server Support

The integration now supports **multiple MCP server options** with automatic fallback:

1. **Atlassian Rovo MCP Server** (Official - Recommended) ⭐
   - **Official Atlassian cloud-based MCP server**
   - Documentation: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
   - Supports Jira, Confluence, and Compass
   - Uses OAuth 2.1 authentication (more secure)
   - Cloud-based (no local installation needed)
   - Currently in Beta

2. **mcp-jira** (by Warzuponus)
   - GitHub: https://github.com/Warzuponus/mcp-jira
   - Popular community package
   - Full Jira functionality
   - Uses API tokens

3. **mcp-atlassian** (by Sooperset)
   - GitHub: https://github.com/sooperset/mcp-atlassian
   - Supports both Jira and Confluence
   - Unified Atlassian integration
   - Uses API tokens

4. **@modelcontextprotocol/server-jira** (Official, if available)
   - Fallback option if official package becomes available

### 🔄 Automatic Fallback

The system automatically:
1. Tries each MCP server package in order
2. Falls back to custom tools if MCP servers are unavailable
3. Provides clear error messages and installation instructions

## Installation

### Prerequisites

1. **Node.js and npm** (already installed)
   ```powershell
   node --version  # Should show v24.11.1 or similar
   npm --version   # Should show version
   ```

2. **MCP SDK** (Python)
   ```powershell
   pip install mcp
   ```

### Install MCP Server Packages

#### Option 1: Atlassian Rovo MCP Server (Official - Recommended) ⭐

The **Atlassian Rovo MCP Server** is Atlassian's official cloud-based solution. It's the recommended option.

**Installation:**
```powershell
npm install -g mcp-remote
```

**Setup:**
1. The Rovo MCP Server uses **OAuth 2.1** authentication
2. On first use, you'll be prompted to complete OAuth flow in your browser
3. No API tokens needed - authentication is handled via OAuth
4. Supports Jira, Confluence, and Compass

**Benefits:**
- ✅ Official Atlassian solution
- ✅ More secure (OAuth 2.1)
- ✅ No API tokens to manage
- ✅ Supports Jira, Confluence, and Compass
- ✅ Cloud-based (no local server needed)

**Documentation:** https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/

#### Option 2: mcp-jira (Community - Jira-only)

```powershell
npm install -g mcp-jira
```

Or use with npx (auto-installs):
```powershell
npx -y mcp-jira
```

#### Option 3: mcp-atlassian (Community - Jira + Confluence)

```powershell
npm install -g mcp-atlassian
```

Or use with npx (auto-installs):
```powershell
npx -y mcp-atlassian
```

## Configuration

### Environment Variables

#### For Atlassian Rovo MCP Server (Official)

**No environment variables needed!** The Rovo MCP Server uses OAuth 2.1 authentication:
- Authentication is handled via browser-based OAuth flow
- No API tokens required
- Access is granted based on your Atlassian account permissions

**First-time setup:**
1. When you first use the Rovo MCP Server, a browser window will open
2. Complete the OAuth authorization flow
3. Grant permissions to the MCP server
4. The connection will be established automatically

#### For Community Packages (mcp-jira, mcp-atlassian)

Set these in your `.env` file or environment:

```env
# Jira Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ

# Confluence Configuration (if using mcp-atlassian)
CONFLUENCE_URL=https://yourcompany.atlassian.net
CONFLUENCE_SPACE_KEY=SPACE
```

### API Token Setup (Community Packages Only)

If using community packages (not Rovo), you'll need an API token:

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token and set it as `JIRA_API_TOKEN`

## How It Works

### Architecture

```
User Request
    ↓
LangGraph Agent
    ↓
MCP Integration
    ├─→ Try MCP Server (mcp-jira or mcp-atlassian)
    │   ├─→ Connect via stdio
    │   ├─→ Discover tools
    │   └─→ Execute tool calls
    │
    └─→ Fallback to Custom Tools (if MCP fails)
        └─→ JiraTool (direct API)
```

### Tool Discovery

When the MCP client connects:
1. Initializes connection to MCP server
2. Discovers available tools
3. Caches tool schemas
4. Exposes tools to the agent

### Tool Execution

Each tool call:
1. Creates a new MCP session
2. Calls the tool with arguments
3. Returns results to the agent
4. Handles errors gracefully

## Available Tools

The exact tools depend on the MCP server package used. Common tools include:

### mcp-jira Tools
- `create_issue` - Create new Jira issues
- `get_issue` - Retrieve issue details
- `search_issues` - Search with JQL
- `update_issue` - Update issue fields
- `add_comment` - Add comments to issues
- `transition_issue` - Move issues through workflow

### mcp-atlassian Tools
- All Jira tools (same as above)
- `create_confluence_page` - Create Confluence pages
- `search_confluence` - Search Confluence content
- `get_confluence_page` - Retrieve page content

## Usage

### In the Chatbot

The integration is automatic. When you use the chatbot:

```python
from src.agent import ChatbotAgent

agent = ChatbotAgent(use_mcp=True)  # MCP enabled by default

# Create a Jira issue
response = agent.invoke("Create a Jira issue for implementing user authentication")
```

### Manual Testing

Test the MCP connection:

```powershell
python test_mcp_connection.py
```

## Troubleshooting

### MCP Server Not Found

**Error**: `MCP server package 'mcp-jira' not found`

**For Atlassian Rovo MCP Server:**
```powershell
npm install -g mcp-remote
```

**For Community Packages:**
```powershell
npm install -g mcp-jira
# or
npm install -g mcp-atlassian
```

### Connection Timeout

**Error**: `Connection timeout to jira MCP server`

**Possible Causes**:
1. MCP server package not installed
2. Network connectivity issues
3. Invalid credentials

**Solution**:
1. Verify package installation: `npm list -g mcp-jira`
2. Check credentials in `.env` file
3. Test with: `npx -y mcp-jira`

### No Tools Available

**Error**: `Available tools: none`

**Possible Causes**:
1. MCP server started but no tools exposed
2. Credentials not configured correctly
3. Server package issue

**Solution**:
1. Check MCP server logs
2. Verify environment variables
3. Try a different MCP server package

### Fallback to Custom Tools

If MCP fails, the chatbot automatically uses custom tools:
- ✅ Still fully functional
- ✅ No user impact
- ✅ Clear logging about fallback

## Benefits

### ✅ Standardized Protocol
- Uses open MCP standard
- Compatible with MCP ecosystem
- Future-proof architecture

### ✅ Community Tools
- Access to community-maintained servers
- Regular updates and improvements
- Active development

### ✅ Flexible
- Easy to switch MCP server packages
- Support for multiple providers
- Extensible architecture

### ✅ Reliable
- Automatic fallback to custom tools
- Error handling and recovery
- Clear error messages

## Comparison: MCP vs Custom Tools

| Feature | MCP Tools | Custom Tools |
|---------|-----------|--------------|
| Standardization | ✅ Open standard | ❌ Custom implementation |
| Community Support | ✅ Active community | ❌ Project-specific |
| Updates | ✅ Package updates | ❌ Manual updates |
| Flexibility | ✅ Multiple providers | ⚠️ Single implementation |
| Reliability | ✅ With fallback | ✅ Always available |
| Setup | ⚠️ Requires npm | ✅ Python only |

## Next Steps

1. **Install MCP Server**: Choose and install `mcp-jira` or `mcp-atlassian`
2. **Configure Credentials**: Set up Jira API token in `.env`
3. **Test Connection**: Run `python test_mcp_connection.py`
4. **Use Chatbot**: Start using the chatbot - MCP will be used automatically!

## Resources

- **Atlassian Rovo MCP Server (Official)**: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
- **MCP Documentation**: https://modelcontextprotocol.io
- **mcp-jira**: https://github.com/Warzuponus/mcp-jira
- **mcp-atlassian**: https://github.com/sooperset/mcp-atlassian
- **Jira API**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/

## Summary

✅ **Updated**: Now supports Atlassian Rovo MCP Server (Official) + community packages  
✅ **Official Support**: Atlassian's official cloud-based MCP server (Recommended)  
✅ **Flexible**: Multiple package options with automatic fallback  
✅ **Secure**: OAuth 2.1 authentication with Rovo (no API tokens needed)  
✅ **Reliable**: Automatic fallback to custom tools  
✅ **Ready**: Fully integrated and ready to use!

### Recommended Setup

1. **Install mcp-remote**: `npm install -g mcp-remote`
2. **Use Atlassian Rovo MCP Server**: Official, secure, and feature-rich
3. **Complete OAuth flow**: On first use, authenticate via browser
4. **Start using**: The chatbot will automatically use Rovo MCP Server

The Jira MCP integration is now complete with official Atlassian support! 🎉

