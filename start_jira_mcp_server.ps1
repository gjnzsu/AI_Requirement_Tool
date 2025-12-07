# PowerShell script to start and test the custom Jira MCP server

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Custom Jira MCP Server - Startup Test" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Check if MCP SDK is installed
Write-Host "Checking MCP SDK installation..." -ForegroundColor Yellow
try {
    $mcpCheck = python -c "import mcp; print('OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ MCP SDK is installed" -ForegroundColor Green
    } else {
        Write-Host "✗ MCP SDK not found. Installing..." -ForegroundColor Red
        pip install mcp
    }
} catch {
    Write-Host "⚠ Could not check MCP SDK" -ForegroundColor Yellow
}

Write-Host ""

# Check Jira credentials
Write-Host "Checking Jira credentials..." -ForegroundColor Yellow
$envFile = ".env"
if (Test-Path $envFile) {
    Write-Host "✓ .env file found" -ForegroundColor Green
} else {
    Write-Host "⚠ .env file not found" -ForegroundColor Yellow
    Write-Host "  Create .env file with Jira credentials" -ForegroundColor Yellow
}

Write-Host ""

# Test the MCP server
Write-Host "Testing custom Jira MCP server..." -ForegroundColor Yellow
Write-Host ""
python test_custom_jira_mcp.py

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Note: The MCP server starts automatically with the chatbot" -ForegroundColor Cyan
Write-Host "      Run: python app.py" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

