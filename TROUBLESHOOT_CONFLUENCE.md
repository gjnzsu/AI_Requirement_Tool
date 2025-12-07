# Troubleshooting Confluence Page Creation

## Quick Diagnosis

When creating a Jira issue, if Confluence page creation fails, check these:

### 1. Check Configuration

Verify your `.env` file has:
```env
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY
```

**Important:** 
- `CONFLUENCE_URL` should end with `/wiki`
- `CONFLUENCE_SPACE_KEY` should be the actual space key (not "SPACE")

### 2. Check Server Startup Logs

When the server starts, you should see:
```
✓ Initialized Confluence Tool
```

If you see:
```
⚠ Confluence Tool not available: ...
```

Then the tool wasn't initialized. Check the error message.

### 3. Common Error Messages

#### "CONFLUENCE_URL is not configured"
**Fix:** Add to `.env`:
```env
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki
```

#### "CONFLUENCE_SPACE_KEY is not configured"
**Fix:** Add to `.env`:
```env
CONFLUENCE_SPACE_KEY=YOUR_ACTUAL_SPACE_KEY
```

#### "HTTP 403: Forbidden"
**Causes:**
- API token doesn't have permission
- Space key is wrong
- User doesn't have access to space

**Fix:**
1. Verify space key in Confluence URL: `https://company.atlassian.net/wiki/spaces/SPACE_KEY/...`
2. Check API token has Confluence write permissions
3. Ensure user has "Create" permission in the space

#### "HTTP 404: Not Found"
**Causes:**
- Confluence URL incorrect
- Space doesn't exist

**Fix:**
1. Verify `CONFLUENCE_URL` ends with `/wiki`
2. Check space key exists in your Confluence instance

#### "Connection timeout" or Network errors
**Fix:**
- Check network connectivity
- Verify firewall allows connections to Confluence
- Check if Confluence URL is accessible

## Testing Confluence Configuration

### Test 1: Check Tool Initialization
```python
from src.tools.confluence_tool import ConfluenceTool
try:
    tool = ConfluenceTool()
    print("✓ Confluence tool initialized successfully")
except Exception as e:
    print(f"✗ Error: {e}")
```

### Test 2: Manual Page Creation
```python
from src.tools.confluence_tool import ConfluenceTool

tool = ConfluenceTool()
result = tool.create_page(
    title="Test Page",
    content="<h1>Test</h1><p>This is a test page.</p>"
)

if result.get('success'):
    print(f"✓ Page created: {result['link']}")
else:
    print(f"✗ Failed: {result.get('error')}")
```

## Debug Steps

1. **Check .env file exists and is loaded**
   ```python
   from config.config import Config
   print(f"CONFLUENCE_URL: {Config.CONFLUENCE_URL}")
   print(f"CONFLUENCE_SPACE_KEY: {Config.CONFLUENCE_SPACE_KEY}")
   ```

2. **Verify API credentials**
   - Same email and token work for Jira
   - Token has Confluence permissions

3. **Test API connection**
   ```python
   import requests
   from requests.auth import HTTPBasicAuth
   from config.config import Config
   
   auth = HTTPBasicAuth(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
   url = f"{Config.CONFLUENCE_URL}/rest/api/space/{Config.CONFLUENCE_SPACE_KEY}"
   
   response = requests.get(url, auth=auth)
   print(f"Status: {response.status_code}")
   print(f"Response: {response.text}")
   ```

4. **Check agent logs**
   - Look for "Creating Confluence page for..." messages
   - Check for error messages in console

## What Changed in the Agent

The agent now:
- ✅ Creates Confluence page even if evaluation fails (as long as Jira was created)
- ✅ Provides detailed error messages with troubleshooting steps
- ✅ Better content formatting
- ✅ More informative logging

## Still Not Working?

If Confluence page creation still fails:

1. **Check the exact error message** in the chatbot response
2. **Review server console logs** for detailed errors
3. **Test with manual tool creation** (see Test 2 above)
4. **Verify Confluence API access** using the debug steps

## Alternative: Skip Confluence

If you don't need Confluence pages, you can disable it:
- Don't set `CONFLUENCE_URL` and `CONFLUENCE_SPACE_KEY`
- The agent will skip Confluence creation
- Jira creation and evaluation will still work

