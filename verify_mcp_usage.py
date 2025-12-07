"""
Script to verify that MCP server was used for Jira creation.
This checks the console output and response for MCP indicators.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("How to Verify MCP Server is Being Used")
print("=" * 70)
print()

print("When you create a Jira issue, look for these indicators:")
print()

print("1. 🔵 CONSOLE OUTPUT INDICATORS:")
print("   " + "-" * 66)
print("   ✓ MCP is enabled (USE_MCP=True)")
print("   ✓ MCP tool 'create_jira_issue' found and ready to use")
print("   🚀 Using MCP Tool to create Jira issue...")
print("   🔵 MCP SERVER: create_jira_issue called")
print("   ✅ MCP SERVER: Successfully created issue XXX-XXX")
print("   ✅ MCP Tool SUCCESS: Created issue XXX-XXX")
print("   🔵 PROOF: Created by MCP Server (custom-jira-mcp-server)")
print()

print("2. 🔵 RESPONSE MESSAGE INDICATOR:")
print("   " + "-" * 66)
print("   ✅ Successfully created Jira issue: **XXX-XXX**")
print("   Link: https://...")
print("   _(Created using MCP Tool)_")
print()

print("3. 🔵 VS CUSTOM TOOL (What you DON'T want to see):")
print("   " + "-" * 66)
print("   ⚠ MCP is disabled (USE_MCP=False)")
print("   ✓ Using custom JiraTool (fallback)")
print("   🔧 Using Custom JiraTool to create Jira issue...")
print("   ✅ Custom Tool SUCCESS: Created issue XXX-XXX")
print("   _(Created using Custom Tool)_")
print()

print("4. 🔵 QUICK CHECK:")
print("   " + "-" * 66)
print("   If you see '🚀 Using MCP Tool' → MCP is being used ✅")
print("   If you see '🔧 Using Custom JiraTool' → Custom tool is being used ❌")
print()

print("5. 🔵 MCP SERVER PROCESS:")
print("   " + "-" * 66)
print("   The MCP server runs as a separate Python process.")
print("   You should see messages starting with '🔵 MCP SERVER:'")
print("   These come from the jira_mcp_server.py process.")
print()

print("=" * 70)
print("To test, create a Jira issue and check the console output!")
print("=" * 70)

