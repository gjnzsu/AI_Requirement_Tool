# MCP Logging Guide - How to Track MCP Usage

## Overview

Enhanced logging has been added throughout the MCP flow to clearly track when the MCP server is being used vs. the custom tool.

## Logging Indicators

### ✅ When MCP is Being Used

Look for these log messages in your console:

#### 1. Initial Check
```
======================================================================
🔧 Jira Creation: Checking available tools...
   Timestamp: 2024-01-15 10:30:45
======================================================================
✓ MCP is enabled (USE_MCP=True)
   📝 LOG: MCP_ENABLED=True at 2024-01-15T10:30:45.123456
```

#### 2. Tool Found
```
🔍 Checking for MCP tool 'create_jira_issue'...
✓ MCP tool 'create_jira_issue' found and ready to use
   📝 LOG: MCP_TOOL_FOUND=True at 2024-01-15T10:30:45.234567
```

#### 3. MCP Tool Selected
```
======================================================================
🚀 USING MCP TOOL TO CREATE JIRA ISSUE
======================================================================
   📝 LOG: TOOL_SELECTED=MCP_TOOL at 2024-01-15T10:30:45.345678
   Summary: Your issue summary...
   Priority: Medium
   Issue Type: Story
   📝 LOG: Calling MCP server process...
======================================================================
   📝 LOG: MCP_TOOL_INVOKE_START at 2024-01-15T10:30:45.456789
```

#### 4. MCP Server Process (Separate Process)
```
======================================================================
🔵 MCP SERVER PROCESS: create_jira_issue called
   📝 LOG: MCP_SERVER_CALLED=True at 2024-01-15T10:30:45.567890
   📝 LOG: PROCESS_ID=12345
   Summary: Your issue summary...
   Priority: Medium
   Issue Type: Story
======================================================================
   📝 LOG: Calling Jira API via jira_client.create_issue()...
======================================================================
✅ MCP SERVER: Successfully created issue SCRUM-26
   Link: https://...
   📝 LOG: ISSUE_CREATED=SCRUM-26 at 2024-01-15T10:30:46.123456
   📝 LOG: API_CALL_DURATION=0.55s
   📝 LOG: CREATED_BY=MCP_SERVER_PROCESS
======================================================================
```

#### 5. Success Confirmation
```
   📝 LOG: MCP_TOOL_INVOKE_COMPLETE at 2024-01-15T10:30:46.234567
======================================================================
✅ MCP TOOL SUCCESS: Created issue SCRUM-26
======================================================================
   Link: https://...
   📝 LOG: ISSUE_CREATED_BY=MCP_SERVER
   📝 LOG: TOOL_USED=custom-jira-mcp-server
   📝 LOG: CREATED_BY=MCP_SERVER
   📝 LOG: SUCCESS_TIMESTAMP=2024-01-15T10:30:46.345678
   🔵 PROOF: Created by MCP Server (custom-jira-mcp-server)
   🔵 PROOF: created_by = MCP_SERVER
======================================================================
```

### ❌ When Custom Tool is Being Used (NOT MCP)

Look for these log messages:

```
======================================================================
🔧 USING CUSTOM JIRATOOL (NOT MCP)
======================================================================
   📝 LOG: TOOL_SELECTED=CUSTOM_TOOL at 2024-01-15T10:30:45.123456
   Summary: Your issue summary...
   Priority: Medium
   📝 LOG: Calling custom JiraTool (direct API call)...
======================================================================
======================================================================
✅ CUSTOM TOOL SUCCESS: Created issue SCRUM-27
======================================================================
   📝 LOG: ISSUE_CREATED_BY=CUSTOM_TOOL
   📝 LOG: TOOL_USED=custom-jira-tool
   📝 LOG: SUCCESS_TIMESTAMP=2024-01-15T10:30:46.123456
======================================================================
```

## Key Differences

| Indicator | MCP Tool | Custom Tool |
|-----------|----------|-------------|
| Tool Selection | `🚀 USING MCP TOOL` | `🔧 USING CUSTOM JIRATOOL` |
| LOG Message | `TOOL_SELECTED=MCP_TOOL` | `TOOL_SELECTED=CUSTOM_TOOL` |
| Server Process | `🔵 MCP SERVER PROCESS` messages | No server process messages |
| Created By | `CREATED_BY=MCP_SERVER` | `CREATED_BY=CUSTOM_TOOL` |
| Tool Used | `TOOL_USED=custom-jira-mcp-server` | `TOOL_USED=custom-jira-tool` |
| Response Message | `_(Created using MCP Tool)_` | `_(Created using Custom Tool)_` |

## Quick Verification Checklist

When creating a Jira issue, check:

- [ ] See `✓ MCP is enabled (USE_MCP=True)`
- [ ] See `✓ MCP tool 'create_jira_issue' found`
- [ ] See `🚀 USING MCP TOOL TO CREATE JIRA ISSUE`
- [ ] See `🔵 MCP SERVER PROCESS: create_jira_issue called`
- [ ] See `✅ MCP SERVER: Successfully created issue`
- [ ] See `✅ MCP TOOL SUCCESS`
- [ ] See `📝 LOG: ISSUE_CREATED_BY=MCP_SERVER`
- [ ] See `🔵 PROOF: Created by MCP Server`
- [ ] Response shows `_(Created using MCP Tool)_`

If you see ALL of these, MCP is definitely being used! ✅

## Troubleshooting

If you see custom tool messages instead:

1. **Check USE_MCP setting:**
   - Look for `⚠ MCP is disabled (USE_MCP=False)`
   - Verify `.env` file has `USE_MCP=true`
   - Restart your Flask app

2. **Check MCP initialization:**
   - Look for `✗ MCP initialization failed`
   - Check MCP server can start
   - Verify Jira credentials are correct

3. **Check tool availability:**
   - Look for `⚠ MCP tool 'create_jira_issue' not available`
   - Verify MCP server is connected
   - Check MCP integration initialized successfully

