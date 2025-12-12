# Community MCP Server Tests - Disabled

## Summary

Community MCP server tests have been disabled because the application does not use community `mcp-jira` package in production.

## Changes Made

### Disabled Test
- **`test_community_jira_servers`** in `test_jira_mcp_server.py`
  - **Reason:** Tests `mcp-jira` and `mcp-atlassian` community packages
  - **Status:** Skipped with `@pytest.mark.skip`
  - **Note:** `mcp-jira` is not used in production (app uses custom Python-based server)

### What the App Actually Uses

#### For Jira:
- ✅ **Custom Python-based MCP Server** (`src/mcp/jira_mcp_server.py`)
  - No npm packages required
  - Fast and reliable
  - Uses credentials from `.env`

#### For Confluence:
- ✅ **Atlassian Rovo MCP Server** (Official - Primary)
  - Uses `mcp-remote` npm package
  - Official Atlassian server
- ✅ **mcp-atlassian** (Community - Fallback)
  - Used only as fallback if Rovo unavailable
  - Not tested in Jira tests (Confluence fallback)

## Test Status

| Test | Status | Reason |
|------|--------|--------|
| `test_community_jira_servers` | ⏭️ SKIPPED | Community `mcp-jira` not used in production |
| `test_custom_jira_mcp` | ✅ ACTIVE | Tests custom Python-based server (used in production) |
| `test_rovo_mcp_server` | ✅ ACTIVE | Tests official Atlassian Rovo server (used for Confluence) |

## Impact

- **Faster test execution:** Community server tests that took 13-30 seconds are now skipped
- **More accurate testing:** Tests now focus on what's actually used in production
- **Reduced dependencies:** No need to download/test unused npm packages

## Running Tests

The disabled test will show as "SKIPPED" when running pytest:

```bash
python -m pytest tests/integration/mcp/ -v
```

Output will show:
```
tests/integration/mcp/test_jira_mcp_server.py::test_community_jira_servers SKIPPED
```

## Re-enabling (if needed)

If you need to test community servers for evaluation purposes, remove the `@pytest.mark.skip` decorator from `test_community_jira_servers` in `test_jira_mcp_server.py`.

