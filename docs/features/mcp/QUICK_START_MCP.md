# Quick Start: Custom Jira MCP Server

## ✅ The MCP Server Starts Automatically!

The custom Jira MCP server **automatically starts** when you start the chatbot. No manual steps needed!

## Start the Chatbot (MCP Server Auto-Starts)

Simply start the chatbot:

```powershell
python app.py
```

The chatbot will:
1. ✅ Automatically start the custom Jira MCP server
2. ✅ Connect to it via stdio
3. ✅ Discover the `create_jira_issue` tool
4. ✅ Make it available for use

## What You'll See

When the chatbot starts, look for these messages:

```
✓ Created custom Jira MCP client (Python-based)
✓ Connected to MCP server: custom-jira
  Available tools: create_jira_issue
✓ MCP Integration initialized with 1 tools
✓ MCP protocol enabled
```

## Verify MCP Server is Running

Test the server connection:

```powershell
python test_custom_jira_mcp.py
```

Expected output:
```
✓ Jira credentials configured
✓ Client created
✓ Connected successfully!
Available tools: 1
  - create_jira_issue
```

## How It Works

1. **Chatbot Starts** → Initializes MCP Integration
2. **MCP Integration** → Spawns Python process: `python src/mcp/jira_mcp_server.py`
3. **MCP Server** → Connects via stdio, registers tools
4. **Tools Available** → `create_jira_issue` ready to use

## Configuration

Ensure `.env` file has:

```env
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ
USE_MCP=true
```

## Troubleshooting

### Server Not Starting

**Check**:
- MCP SDK installed: `pip install mcp`
- Jira credentials configured in `.env`
- Python can execute the server script

### Connection Timeout

**Check**:
- Jira credentials are valid
- Network connectivity to Jira
- Jira API token has correct permissions

## Summary

✅ **Automatic**: Server starts with chatbot  
✅ **No Manual Steps**: Just start `python app.py`  
✅ **Ready to Use**: `create_jira_issue` tool available  
✅ **Reliable**: Uses your own tested code  

**Just start the chatbot - the MCP server will start automatically!** 🚀

