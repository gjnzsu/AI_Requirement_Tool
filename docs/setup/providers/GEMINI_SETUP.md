# Gemini Pro Configuration Guide

This guide will help you set up Google Gemini Pro for the Jira Maturity Evaluator service.

## Step 1: Get Your Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key (starts with `AIza...`)
5. Keep it secure - you won't be able to see it again!

## Step 2: Install Gemini SDK

Install the required package:

```powershell
pip install google-generativeai
```

Or install all requirements:

```powershell
pip install -r requirements-jira-service.txt
```

## Step 3: Configure Environment Variables

### Option A: PowerShell (Current Session)

**Basic Configuration (without proxy):**
```powershell
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="your-gemini-api-key-here"
$env:GEMINI_MODEL="gemini-pro"  # Options: gemini-pro, gemini-1.5-pro, gemini-1.5-flash
```

**With Proxy Configuration:**
```powershell
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="your-gemini-api-key-here"
$env:GEMINI_MODEL="gemini-pro"
$env:GEMINI_PROXY="http://proxy.example.com:8080"  # HTTP proxy
# OR
$env:GEMINI_PROXY="socks5://proxy.example.com:1080"  # SOCKS5 proxy
```

### Option B: .env File (Recommended)

Create or edit `.env` file in the project root:

**Without Proxy:**
```env
# LLM Provider Configuration
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-pro

# Jira Configuration (keep your existing values)
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=PROJ
```

**With Proxy:**
```env
# LLM Provider Configuration
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-pro
GEMINI_PROXY=http://proxy.example.com:8080  # HTTP proxy
# OR use standard proxy variables:
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080

# Jira Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=PROJ
```

### Option C: Use Setup Script

Run the automated setup script:

```powershell
.\setup_gemini.ps1
```

## Step 4: Test Configuration

Test if Gemini is properly configured:

```powershell
python test_gemini.py
```

This will verify:
- ✅ API key is set
- ✅ Package is installed
- ✅ API connection works
- ✅ Model responds correctly

## Step 5: Run the Service

Once configured, run the evaluation service:

```powershell
python evaluate_jira_maturity.py
```

## Available Gemini Models

- **gemini-pro**: Standard Gemini Pro model (default)
- **gemini-1.5-pro**: Latest Pro model with improved capabilities
- **gemini-1.5-flash**: Faster, lighter model for quick responses

## Proxy Configuration

If you need to use a proxy to access the Gemini API (common in corporate networks or restricted regions):

### Proxy Format

- **HTTP Proxy:** `http://proxy.example.com:8080`
- **HTTPS Proxy:** `https://proxy.example.com:8080`
- **SOCKS5 Proxy:** `socks5://proxy.example.com:1080`
- **With Authentication:** `http://username:password@proxy.example.com:8080`

### Setting Proxy

**Method 1: GEMINI_PROXY (Recommended)**
```powershell
$env:GEMINI_PROXY="http://proxy.example.com:8080"
```

**Method 2: Standard HTTP_PROXY/HTTPS_PROXY**
```powershell
$env:HTTP_PROXY="http://proxy.example.com:8080"
$env:HTTPS_PROXY="http://proxy.example.com:8080"
```

**Method 3: In .env file**
```env
GEMINI_PROXY=http://proxy.example.com:8080
```

### Testing Proxy Connection

After setting the proxy, test the connection:
```powershell
python test_gemini.py
```

If the proxy requires authentication:
```powershell
$env:GEMINI_PROXY="http://username:password@proxy.example.com:8080"
```

## Troubleshooting

### Error: "google-generativeai package is required"
**Solution:** Install the package:
```powershell
pip install google-generativeai
```

### Error: "API key not valid"
**Solution:** 
- Verify your API key is correct
- Check if you copied the full key
- Ensure you're using the API key from Google AI Studio

### Error: "Connection timeout" or "Unable to connect"
**Solution:**
- Check if proxy is configured correctly
- Verify proxy server is accessible
- Test proxy connection: `curl -x http://proxy.example.com:8080 https://generativelanguage.googleapis.com`
- Check firewall settings

### Error: "Proxy authentication required"
**Solution:**
- Include credentials in proxy URL: `http://username:password@proxy.example.com:8080`
- Verify proxy credentials are correct

### Error: "Quota exceeded" or "Rate limit"
**Solution:**
- Check your Google Cloud quota limits
- Wait a few minutes and try again
- Consider using a different model (gemini-1.5-flash is faster)

### Error: "Model not found"
**Solution:**
- Verify the model name is correct
- Check available models: https://ai.google.dev/models/gemini
- Try using `gemini-pro` (most widely available)

## Quick Reference

**Current Configuration Check:**
```powershell
python -c "from config.config import Config; print(f'Provider: {Config.LLM_PROVIDER}, Model: {Config.GEMINI_MODEL}')"
```

**Switch Back to OpenAI:**
```powershell
$env:LLM_PROVIDER="openai"
```

**Switch to DeepSeek:**
```powershell
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="your-deepseek-key"
```

## Example .env File

**Without Proxy:**
```env
# LLM Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyC_your_actual_api_key_here
GEMINI_MODEL=gemini-pro

# Jira
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-token
JIRA_PROJECT_KEY=SCRUM

# Settings
MAX_BACKLOG_ITEMS=50
```

**With Proxy:**
```env
# LLM Provider
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyC_your_actual_api_key_here
GEMINI_MODEL=gemini-pro
GEMINI_PROXY=http://proxy.example.com:8080

# Jira
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-token
JIRA_PROJECT_KEY=SCRUM

# Settings
MAX_BACKLOG_ITEMS=50
```

