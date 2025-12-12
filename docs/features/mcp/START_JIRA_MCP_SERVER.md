# Starting the Custom Jira MCP Server

## Quick Start

The custom Jira MCP server is **automatically started** by the chatbot when MCP is enabled. You don't need to start it manually!

However, if you want to test it independently or run it standalone, here's how:

## Method 1: Automatic (Recommended)

The chatbot automatically starts the MCP server when:
- MCP is enabled (`USE_MCP=true` or not set)
- Jira credentials are configured
- You start the chatbot

**Just start the chatbot normally:**
```powershell
python app.py
```

The MCP server will start automatically in the background.

## Method 2: Test the Server

Test the server connection:

```powershell
python test_custom_jira_mcp.py
```

This will:
- ✅ Check Jira credentials
- ✅ Create MCP client
- ✅ Connect to server
- ✅ List available tools
- ✅ Test creating a Jira issue

## Method 3: Run Server Standalone (For Debugging)

If you want to run the server standalone for debugging:

```powershell
python src/mcp/jira_mcp_server.py
```

**Note**: The server runs via stdio (standard input/output), so it's designed to be started by the MCP client, not run directly. Running it standalone will wait for MCP protocol messages on stdin.

## Verification

When the chatbot starts, you should see:

```
✓ Created custom Jira MCP client (Python-based)
✓ Connected to MCP server: custom-jira
  Available tools: create_jira_issue
✓ MCP Integration initialized with 1 tools
```

## Troubleshooting

### Server Won't Start

**Error**: `MCP server SDK not installed`

**Solution**:
```powershell
pip install mcp
```

### Connection Timeout

**Error**: `Connection timeout`

**Check**:
1. Jira credentials in `.env` file
2. Network connectivity to Jira
3. Jira API token is valid

### No Tools Available

**Error**: `Available tools: none`

**Check**:
1. Server started successfully
2. Jira connection initialized
3. Check server logs (stderr)

## Configuration

Ensure your `.env` file has:

```env
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJ
USE_MCP=true
```

## Summary

✅ **Automatic**: Server starts automatically with chatbot  
✅ **No Manual Steps**: Just configure credentials and start chatbot  
✅ **Test Available**: Use `test_custom_jira_mcp.py` to verify  
✅ **Reliable**: Uses your own tested code  

The custom Jira MCP server is ready to use! 🎉

