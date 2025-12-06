# PowerShell script to switch to OpenAI ChatGPT
# Usage: .\switch_to_openai.ps1 -ApiKey "your-api-key-here" -Model "gpt-3.5-turbo"

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    
    [Parameter(Mandatory=$false)]
    [string]$Model = "gpt-3.5-turbo"
)

$envFile = Join-Path $PSScriptRoot ".env"

Write-Host "Switching chatbot to OpenAI ChatGPT..." -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (Test-Path $envFile) {
    Write-Host "Found .env file. Updating configuration..." -ForegroundColor Yellow
    
    # Read existing .env file
    $content = Get-Content $envFile
    
    # Update or add LLM_PROVIDER
    if ($content -match "^LLM_PROVIDER=") {
        $content = $content -replace "^LLM_PROVIDER=.*", "LLM_PROVIDER=openai"
    } else {
        $content += "LLM_PROVIDER=openai"
    }
    
    # Update or add OPENAI_API_KEY
    if ($content -match "^OPENAI_API_KEY=") {
        $content = $content -replace "^OPENAI_API_KEY=.*", "OPENAI_API_KEY=$ApiKey"
    } else {
        $content += "OPENAI_API_KEY=$ApiKey"
    }
    
    # Update or add OPENAI_MODEL
    if ($content -match "^OPENAI_MODEL=") {
        $content = $content -replace "^OPENAI_MODEL=.*", "OPENAI_MODEL=$Model"
    } else {
        $content += "OPENAI_MODEL=$Model"
    }
    
    # Write back to file
    $content | Set-Content $envFile
    
    Write-Host "✓ Updated .env file successfully!" -ForegroundColor Green
} else {
    Write-Host ".env file not found. Creating new one..." -ForegroundColor Yellow
    
    # Create new .env file
    @"
# LLM Provider Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=$ApiKey
OPENAI_MODEL=$Model
"@ | Set-Content $envFile
    
    Write-Host "✓ Created .env file successfully!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Configuration updated:" -ForegroundColor Cyan
Write-Host "  Provider: openai" -ForegroundColor White
Write-Host "  Model: $Model" -ForegroundColor White
Write-Host "  API Key: $($ApiKey.Substring(0, [Math]::Min(10, $ApiKey.Length)))..." -ForegroundColor White
Write-Host ""
Write-Host "You can now run: python src/chatbot.py" -ForegroundColor Green

