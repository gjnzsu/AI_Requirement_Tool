# PowerShell script to set environment variables for Jira Maturity Evaluator Service
# Usage: .\set-env.ps1

# Jira Configuration
$env:JIRA_URL="https://yourcompany.atlassian.net"
$env:JIRA_EMAIL="your-email@example.com"
$env:JIRA_API_TOKEN="your-jira-api-token"
$env:JIRA_PROJECT_KEY="PROJ"

# OpenAI Configuration
$env:OPENAI_API_KEY="your-openai-api-key"
$env:OPENAI_MODEL="gpt-4"

# Evaluation Settings
$env:MAX_BACKLOG_ITEMS="50"

Write-Host "Environment variables set for current PowerShell session!" -ForegroundColor Green
Write-Host ""
Write-Host "To verify, run:" -ForegroundColor Yellow
Write-Host "  `$env:JIRA_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the service:" -ForegroundColor Yellow
Write-Host "  python evaluate_jira_maturity.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: These variables only last for this PowerShell session." -ForegroundColor Gray
Write-Host "To make them permanent, use Method 2 in SETUP_ENV.md" -ForegroundColor Gray

