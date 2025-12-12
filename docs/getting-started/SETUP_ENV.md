# Setting Environment Variables on Windows

This guide shows you how to set environment variables for the Jira Maturity Evaluator Service on Windows.

## Method 1: PowerShell (Current Session Only)

Since you're using PowerShell, you can set environment variables for the current session:

```powershell
$env:JIRA_URL="https://yourcompany.atlassian.net"
$env:JIRA_EMAIL="your-email@example.com"
$env:JIRA_API_TOKEN="your-jira-api-token"
$env:JIRA_PROJECT_KEY="PROJ"
$env:OPENAI_API_KEY="your-openai-api-key"
$env:MAX_BACKLOG_ITEMS="50"
```

**Note:** These variables only last for the current PowerShell session. They will be lost when you close the terminal.

## Method 2: PowerShell (Permanent - User Level)

To set environment variables permanently for your user account:

```powershell
[System.Environment]::SetEnvironmentVariable('JIRA_URL', 'https://yourcompany.atlassian.net', 'User')
[System.Environment]::SetEnvironmentVariable('JIRA_EMAIL', 'your-email@example.com', 'User')
[System.Environment]::SetEnvironmentVariable('JIRA_API_TOKEN', 'your-jira-api-token', 'User')
[System.Environment]::SetEnvironmentVariable('JIRA_PROJECT_KEY', 'PROJ', 'User')
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'your-openai-api-key', 'User')
[System.Environment]::SetEnvironmentVariable('MAX_BACKLOG_ITEMS', '50', 'User')
```

**Note:** You'll need to restart your terminal/PowerShell for these to take effect.

## Method 3: Command Prompt (CMD)

If you're using Command Prompt instead:

```cmd
set JIRA_URL=https://yourcompany.atlassian.net
set JIRA_EMAIL=your-email@example.com
set JIRA_API_TOKEN=your-jira-api-token
set JIRA_PROJECT_KEY=PROJ
set OPENAI_API_KEY=your-openai-api-key
set MAX_BACKLOG_ITEMS=50
```

**Note:** These only last for the current CMD session.

## Method 4: Using .env File (Recommended - Easiest!)

The easiest way is to use a `.env` file. The service supports this via `python-dotenv`.

1. Create a `.env` file in the project root directory (`generative-ai-chatbot/`)
2. Add your variables (one per line):

```
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=PROJ
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
MAX_BACKLOG_ITEMS=50
```

3. The `.env` file is already in `.gitignore`, so it won't be committed to git.

**Note:** You may need to update the config.py to load from .env file. See below.

## Method 5: Windows GUI (Permanent)

1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Add each variable:
   - Variable name: `JIRA_URL`
   - Variable value: `https://yourcompany.atlassian.net`
6. Repeat for all variables
7. Click OK and restart your terminal

## Quick Setup Script

You can also create a PowerShell script to set all variables at once. Create a file `set-env.ps1`:

```powershell
# Set environment variables for Jira Maturity Evaluator
$env:JIRA_URL="https://yourcompany.atlassian.net"
$env:JIRA_EMAIL="your-email@example.com"
$env:JIRA_API_TOKEN="your-jira-api-token"
$env:JIRA_PROJECT_KEY="PROJ"
$env:OPENAI_API_KEY="your-openai-api-key"
$env:MAX_BACKLOG_ITEMS="50"

Write-Host "Environment variables set for current session!"
Write-Host "Run: python evaluate_jira_maturity.py"
```

Then run: `.\set-env.ps1`

## Verifying Environment Variables

To check if your variables are set in PowerShell:

```powershell
$env:JIRA_URL
$env:OPENAI_API_KEY
```

Or see all environment variables:
```powershell
Get-ChildItem Env: | Where-Object Name -like "JIRA_*"
Get-ChildItem Env: | Where-Object Name -like "OPENAI_*"
```

## Security Note

⚠️ **Never commit your API tokens or credentials to git!** The `.env` file is already in `.gitignore` for your protection.

