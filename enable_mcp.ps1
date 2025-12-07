# PowerShell script to enable MCP for the chatbot
# Usage: .\enable_mcp.ps1

# Enable MCP
$env:USE_MCP="true"

Write-Host "✅ MCP enabled (USE_MCP=true)" -ForegroundColor Green
Write-Host ""
Write-Host "To verify, run:" -ForegroundColor Yellow
Write-Host "  `$env:USE_MCP" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: This only lasts for the current PowerShell session." -ForegroundColor Gray
Write-Host "To make it permanent, add USE_MCP=true to your .env file or system environment variables." -ForegroundColor Gray

