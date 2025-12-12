# MCP Windows Compatibility Fix

## Issue

On Windows, you may see this error when trying to use MCP:
```
✗ Failed to connect to MCP server jira: [WinError 193] %1 不是有效的 Win32 应用程序。
```

This means Node.js/npx is not available or not working correctly on Windows.

## Solution

The chatbot now automatically:
1. ✅ **Checks if Node.js/npx is available** before trying to use MCP
2. ✅ **Falls back to custom tools** if MCP is not available
3. ✅ **Provides clear error messages** about what's missing

## What Happens Now

### If Node.js is NOT installed:
```
⚠ Node.js/npx not found. MCP requires Node.js to run MCP servers.
   Install Node.js from: https://nodejs.org/
   Falling back to custom tools
```

The chatbot will use **custom tools** (JiraTool, ConfluenceTool) instead.

### If Node.js IS installed:
MCP will be used automatically if available.

## To Use MCP on Windows

### Option 1: Install Node.js (Recommended for MCP)

1. **Download Node.js**: https://nodejs.org/
2. **Install it** (includes npm and npx)
3. **Restart your terminal/IDE**
4. **Restart the chatbot server**

The chatbot will automatically detect Node.js and use MCP.

### Option 2: Use Custom Tools (No Node.js needed)

If you don't want to install Node.js, the chatbot will automatically use custom tools. No action needed!

## Verification

### Check if Node.js is installed:
```powershell
node --version
npx --version
```

### Check which tools are being used:

When the chatbot starts, look for:

**Using MCP:**
```
✓ MCP Integration initialized with X tools
```

**Using Custom Tools:**
```
⚠ Node.js/npx not found...
   Falling back to custom tools
✓ Initialized Jira Tool
✓ Initialized Confluence Tool
```

## Both Work the Same!

Whether using MCP or custom tools, the functionality is identical:
- ✅ Create Jira issues
- ✅ Create Confluence pages
- ✅ Evaluate maturity
- ✅ All features work the same

The only difference is the underlying implementation (MCP protocol vs custom tools).

## Summary

- **No impact on functionality** - Custom tools work perfectly
- **Automatic fallback** - No manual configuration needed
- **Clear error messages** - You'll know what's happening
- **Install Node.js** - Only if you specifically want to use MCP protocol

The chatbot will work perfectly with or without MCP! 🎉

