# PowerShell script to configure Gemini Pro for Jira Maturity Evaluator
# Usage: .\setup_gemini.ps1

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Gemini Pro Configuration Setup" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if google-generativeai is installed
Write-Host "Checking for google-generativeai package..." -ForegroundColor Yellow
$packageInstalled = pip show google-generativeai 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ google-generativeai not installed" -ForegroundColor Red
    Write-Host "  Installing google-generativeai..." -ForegroundColor Yellow
    pip install google-generativeai
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Installed successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Installation failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  ✓ google-generativeai is installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setting environment variables for current session..." -ForegroundColor Yellow

# Set LLM provider to Gemini
$env:LLM_PROVIDER="gemini"
Write-Host "  ✓ LLM_PROVIDER=gemini" -ForegroundColor Green

# Prompt for Gemini API key
Write-Host ""
Write-Host "Please enter your Gemini API key:" -ForegroundColor Yellow
Write-Host "(Get it from: https://makersuite.google.com/app/apikey)" -ForegroundColor Gray
$apiKey = Read-Host "Gemini API Key"

if ($apiKey) {
    $env:GEMINI_API_KEY=$apiKey
    Write-Host "  ✓ GEMINI_API_KEY set" -ForegroundColor Green
} else {
    Write-Host "  ✗ No API key provided" -ForegroundColor Red
    exit 1
}

# Set Gemini model (default: gemini-pro)
Write-Host ""
Write-Host "Select Gemini model:" -ForegroundColor Yellow
Write-Host "  1) gemini-pro (default)"
Write-Host "  2) gemini-1.5-pro"
Write-Host "  3) gemini-1.5-flash"
Write-Host "  4) Custom model name"
$choice = Read-Host "Enter choice (1-4, default: 1)"

switch ($choice) {
    "2" { $model = "gemini-1.5-pro" }
    "3" { $model = "gemini-1.5-flash" }
    "4" { 
        $model = Read-Host "Enter custom model name"
    }
    default { $model = "gemini-pro" }
}

$env:GEMINI_MODEL=$model
Write-Host "  ✓ GEMINI_MODEL=$model" -ForegroundColor Green

# Ask about proxy
Write-Host ""
Write-Host "Do you need to configure a proxy to access Gemini API? (y/n)" -ForegroundColor Yellow
$needProxy = Read-Host "Enter choice (default: n)"

if ($needProxy -eq "y" -or $needProxy -eq "Y") {
    Write-Host ""
    Write-Host "Enter proxy URL:" -ForegroundColor Yellow
    Write-Host "  Examples:" -ForegroundColor Gray
    Write-Host "    http://proxy.example.com:8080" -ForegroundColor Gray
    Write-Host "    socks5://proxy.example.com:1080" -ForegroundColor Gray
    Write-Host "    http://username:password@proxy.example.com:8080" -ForegroundColor Gray
    $proxyUrl = Read-Host "Proxy URL"
    
    if ($proxyUrl) {
        $env:GEMINI_PROXY=$proxyUrl
        Write-Host "  ✓ GEMINI_PROXY=$proxyUrl" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Configuration Complete!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Current configuration:" -ForegroundColor Yellow
Write-Host "  LLM_PROVIDER: $env:LLM_PROVIDER"
Write-Host "  GEMINI_MODEL: $env:GEMINI_MODEL"
Write-Host "  GEMINI_API_KEY: $($env:GEMINI_API_KEY.Substring(0, [Math]::Min(10, $env:GEMINI_API_KEY.Length)))..."
if ($env:GEMINI_PROXY) {
    Write-Host "  GEMINI_PROXY: $env:GEMINI_PROXY"
}
Write-Host ""
Write-Host "To test the configuration, run:" -ForegroundColor Yellow
Write-Host "  python test_gemini.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the service:" -ForegroundColor Yellow
Write-Host "  python evaluate_jira_maturity.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: These environment variables only last for this PowerShell session." -ForegroundColor Gray
Write-Host "To make them permanent, add them to your .env file or use System Properties." -ForegroundColor Gray

