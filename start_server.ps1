# PowerShell script to start the Chatbot Web Server
# Usage: .\start_server.ps1

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host "🤖 Starting Chatbot Web Server" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 69) -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "app.py")) {
    Write-Host "⚠ Error: app.py not found!" -ForegroundColor Red
    Write-Host "   Please run this script from the generative-ai-chatbot directory" -ForegroundColor Yellow
    exit 1
}

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found! Please install Python first." -ForegroundColor Red
    exit 1
}

# Check if port 5000 is available
$portInUse = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠ Warning: Port 5000 is already in use!" -ForegroundColor Yellow
    Write-Host "   You may need to stop the existing server or use a different port" -ForegroundColor Yellow
    Write-Host ""
}

# Check for .env file
if (Test-Path ".env") {
    Write-Host "✓ Found .env configuration file" -ForegroundColor Green
} else {
    Write-Host "⚠ Warning: .env file not found" -ForegroundColor Yellow
    Write-Host "   Make sure your API keys are set in environment variables" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting Flask server..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Once started, open your browser and navigate to:" -ForegroundColor White
Write-Host "  http://localhost:5000" -ForegroundColor Green -BackgroundColor Black
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Start the server
python app.py

