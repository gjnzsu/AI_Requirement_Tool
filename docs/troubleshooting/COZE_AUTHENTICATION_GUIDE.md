# Coze API Authentication Troubleshooting Guide

## Common 401 Error Causes

A 401 Unauthorized error with Coze API typically indicates an authentication issue. Here are the most common causes and solutions:

### 1. **Incorrect or Missing API Token**

**Symptoms:**
- Error code: 4101
- Message: "The token you entered is incorrect"

**Solutions:**
- Verify your `COZE_API_TOKEN` environment variable is set correctly
- Check for extra spaces, newlines, or special characters
- Ensure the token is complete (not truncated)
- Copy the token directly from Coze platform without modifications

**How to get a valid token:**
1. Log in to Coze platform: https://www.coze.com (or https://www.coze.cn for China)
2. Navigate to **Developer Console** or **API Management**
3. Create or copy your **Personal Access Token (PAT)** or **API Key**
4. Ensure the token has proper permissions for bot access

### 2. **Token Format Issues**

**Coze API Token Formats:**
- **PAT (Personal Access Token)**: Usually starts with `pat-` prefix
- **API Key**: May have different format depending on Coze version

**Current Implementation:**
- Uses `Authorization: Bearer {token}` header format
- Works for both PAT and API key formats

**If you're using PAT format:**
- Ensure the token includes the `pat-` prefix
- The full token should be used in `COZE_API_TOKEN`

### 3. **Incorrect Bot ID**

**Symptoms:**
- Error code: 4102 (if bot-specific)
- 401 error if bot ID is required for authentication

**Solutions:**
- Verify your `COZE_BOT_ID` environment variable
- Ensure the Bot ID matches exactly (case-sensitive)
- Check that the bot is published and has API access enabled
- Verify the bot belongs to your account/organization

**How to get Bot ID:**
1. Go to your Coze project
2. Select the bot/agent you want to use
3. Copy the Bot ID from the bot settings/details page
4. Ensure the bot is published with API option enabled

### 4. **Wrong API Base URL**

**Symptoms:**
- 401 errors or connection failures

**Solutions:**
- For **coze.com** (International): Use `https://api.coze.com`
- For **coze.cn** (China): Use `https://api.coze.cn`
- Set `COZE_API_BASE_URL` environment variable if different

### 5. **Expired or Revoked Token**

**Symptoms:**
- Previously working integration suddenly returns 401

**Solutions:**
- Check if token has expiration date
- Generate a new token from Coze platform
- Update `COZE_API_TOKEN` with new token
- Restart the application after updating

### 6. **Insufficient Permissions**

**Symptoms:**
- 401 or 403 errors even with valid token

**Solutions:**
- Verify token has permissions to access bots
- Check token scope/permissions in Coze platform
- Ensure token has "bot access" or "API access" permissions
- Contact Coze support if permissions seem correct but still failing

## Configuration Checklist

Use this checklist to verify your configuration:

```bash
# 1. Check environment variables are set
echo $COZE_ENABLED      # Should be "true"
echo $COZE_API_TOKEN    # Should show token (not empty)
echo $COZE_BOT_ID       # Should show bot ID (not empty)
echo $COZE_API_BASE_URL # Should be https://api.coze.com or https://api.coze.cn

# 2. Run diagnostic script
python scripts/check_coze_config.py
```

## Environment Variable Setup

### Windows PowerShell:
```powershell
$env:COZE_ENABLED = "true"
$env:COZE_API_TOKEN = "your-token-here"
$env:COZE_BOT_ID = "your-bot-id-here"
$env:COZE_API_BASE_URL = "https://api.coze.com"  # Optional
```

### Windows CMD:
```cmd
set COZE_ENABLED=true
set COZE_API_TOKEN=your-token-here
set COZE_BOT_ID=your-bot-id-here
set COZE_API_BASE_URL=https://api.coze.com
```

### Linux/Mac:
```bash
export COZE_ENABLED=true
export COZE_API_TOKEN=your-token-here
export COZE_BOT_ID=your-bot-id-here
export COZE_API_BASE_URL=https://api.coze.com
```

### .env File:
Create a `.env` file in the project root:
```env
COZE_ENABLED=true
COZE_API_TOKEN=your-token-here
COZE_BOT_ID=your-bot-id-here
COZE_API_BASE_URL=https://api.coze.com
```

## Testing Authentication

### 1. Run Diagnostic Script
```bash
python scripts/check_coze_config.py
```

This will show:
- Environment variable status
- Config class values
- Client initialization status
- Token format information
- Troubleshooting steps

### 2. Test with curl (if available)
```bash
curl -X POST https://api.coze.com/open_api/v2/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_id": "YOUR_BOT_ID",
    "user_id": "test_user",
    "query": "hello"
  }'
```

### 3. Check Application Logs
Look for these log messages:
- `Calling Coze API: endpoint=...` - Shows endpoint being used
- `Auth header format: Authorization: Bearer ...` - Shows auth header format
- `Coze API error: code=4101` - Shows specific error code

## Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 4101 | Token incorrect | Check `COZE_API_TOKEN` is correct |
| 4102 | Bot not found | Check `COZE_BOT_ID` is correct |
| 401 | Authentication failed | Verify token and permissions |
| 403 | Access forbidden | Check bot permissions and token scope |

## Still Having Issues?

1. **Double-check token format:**
   - No extra spaces before/after
   - No newlines or special characters
   - Complete token (not truncated)

2. **Verify bot configuration:**
   - Bot is published
   - API access is enabled
   - Bot ID is correct

3. **Check Coze platform status:**
   - Visit Coze status page (if available)
   - Check for platform maintenance

4. **Review Coze documentation:**
   - https://coze.com/docs/developer_guides/authentication
   - Check for recent API changes

5. **Contact support:**
   - Coze platform support
   - Include error code (4101) and logid from error response

## Debug Mode

Enable debug logging to see detailed API requests:

```python
# In your .env or environment
LOG_LEVEL=DEBUG
ENABLE_DEBUG_LOGGING=true
```

This will show:
- Full API endpoint URLs
- Request headers (token preview)
- Response details
- Error information

