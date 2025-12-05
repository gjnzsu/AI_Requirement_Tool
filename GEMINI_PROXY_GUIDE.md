# Gemini Proxy Configuration Guide

This guide explains how to configure proxy settings for accessing the Gemini API, which is often required in corporate networks or restricted regions.

## Why Proxy is Needed

- Corporate firewalls blocking direct API access
- Regional restrictions on Google services
- Network security policies
- VPN requirements

## Quick Setup

### Method 1: Environment Variable (PowerShell)

```powershell
# Set proxy
$env:GEMINI_PROXY="http://proxy.example.com:8080"

# Or with authentication
$env:GEMINI_PROXY="http://username:password@proxy.example.com:8080"
```

### Method 2: .env File

Add to your `.env` file:

```env
GEMINI_PROXY=http://proxy.example.com:8080
```

### Method 3: Standard Proxy Variables

You can also use standard HTTP proxy environment variables:

```powershell
$env:HTTP_PROXY="http://proxy.example.com:8080"
$env:HTTPS_PROXY="http://proxy.example.com:8080"
```

## Proxy URL Formats

### HTTP Proxy
```
http://proxy.example.com:8080
```

### HTTPS Proxy
```
https://proxy.example.com:8080
```

### SOCKS5 Proxy
```
socks5://proxy.example.com:1080
```

### With Authentication
```
http://username:password@proxy.example.com:8080
```

### With Domain Authentication
```
http://DOMAIN\username:password@proxy.example.com:8080
```

## Complete Example

### PowerShell Setup

```powershell
# Basic Gemini configuration
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="AIzaSyC_your_api_key_here"
$env:GEMINI_MODEL="gemini-pro"

# Proxy configuration
$env:GEMINI_PROXY="http://proxy.company.com:8080"

# Test configuration
python test_gemini.py

# Run service
python evaluate_jira_maturity.py
```

### .env File Example

```env
# LLM Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyC_your_api_key_here
GEMINI_MODEL=gemini-pro

# Proxy Configuration
GEMINI_PROXY=http://proxy.company.com:8080

# Jira Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-token
JIRA_PROJECT_KEY=SCRUM
```

## Testing Proxy Connection

### Test 1: Using test_gemini.py

```powershell
python test_gemini.py
```

This will:
- Verify proxy is configured
- Test API connection through proxy
- Show connection status

### Test 2: Manual Proxy Test

Test if proxy works for Google API:

```powershell
# Test HTTP connection through proxy
curl -x http://proxy.example.com:8080 https://generativelanguage.googleapis.com
```

### Test 3: Python Test

```python
import os
os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy.example.com:8080'

import requests
response = requests.get('https://generativelanguage.googleapis.com')
print(response.status_code)
```

## Troubleshooting

### Error: "Connection timeout"

**Possible causes:**
- Proxy server is not accessible
- Proxy URL is incorrect
- Firewall blocking proxy connection

**Solutions:**
1. Verify proxy server is reachable:
   ```powershell
   Test-NetConnection -ComputerName proxy.example.com -Port 8080
   ```

2. Check proxy URL format:
   - Must include protocol: `http://` or `https://`
   - Must include port number: `:8080`
   - No trailing slash

3. Test with curl:
   ```powershell
   curl -x http://proxy.example.com:8080 https://www.google.com
   ```

### Error: "Proxy authentication required"

**Solution:**
Include credentials in proxy URL:
```powershell
$env:GEMINI_PROXY="http://username:password@proxy.example.com:8080"
```

**Note:** Special characters in password may need URL encoding:
- `@` → `%40`
- `:` → `%3A`
- `#` → `%23`
- `%` → `%25`

### Error: "SSL certificate verification failed"

**Solution:**
If your proxy uses a self-signed certificate, you may need to:
1. Add certificate to system trust store, OR
2. Set environment variable (not recommended for production):
   ```powershell
   $env:CURL_CA_BUNDLE=""
   $env:REQUESTS_CA_BUNDLE=""
   ```

### Error: "SOCKS proxy not supported"

**Solution:**
- Use HTTP/HTTPS proxy instead of SOCKS5
- Or install `requests[socks]` and `PySocks`:
  ```powershell
  pip install requests[socks] PySocks
  ```

## Common Corporate Proxy Scenarios

### Scenario 1: Corporate HTTP Proxy

```powershell
$env:GEMINI_PROXY="http://proxy.corp.com:8080"
```

### Scenario 2: Authenticated Proxy

```powershell
$env:GEMINI_PROXY="http://DOMAIN\username:password@proxy.corp.com:8080"
```

### Scenario 3: PAC File Configuration

If your company uses PAC files, you'll need to:
1. Extract proxy server from PAC file
2. Use the extracted proxy URL
3. Or use a PAC file parser library

### Scenario 4: Multiple Proxies

If different proxies are needed for different domains:
- Use `GEMINI_PROXY` specifically for Gemini API
- Keep `HTTP_PROXY`/`HTTPS_PROXY` for other services

## Security Considerations

⚠️ **Important:**
- Never commit proxy credentials to git
- Use `.env` file (already in `.gitignore`)
- Consider using environment variables instead of hardcoding
- Rotate proxy credentials regularly
- Use HTTPS proxy when possible

## Getting Proxy Information

### From Windows Settings

1. Open **Settings** → **Network & Internet** → **Proxy**
2. Check "Manual proxy setup"
3. Note the proxy address and port

### From Internet Explorer Settings

1. Open **Internet Options** → **Connections** → **LAN Settings**
2. Check proxy server settings
3. Copy address and port

### From PowerShell

```powershell
# Check system proxy settings
[System.Net.WebRequest]::GetSystemWebProxy()
```

## Additional Resources

- [Google Generative AI Python SDK](https://github.com/google/generative-ai-python)
- [Python Requests Proxy Documentation](https://requests.readthedocs.io/en/latest/user/advanced/#proxies)
- [Corporate Proxy Configuration](https://docs.python.org/3/library/urllib.request.html#urllib.request.ProxyHandler)

