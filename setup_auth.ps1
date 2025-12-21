# PowerShell script to set up authentication configuration

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Authentication Setup" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

$envFile = ".env"
$jwtSecretKey = ""

# Check if .env file exists
if (Test-Path $envFile) {
    Write-Host "`n✓ .env file found" -ForegroundColor Green
    
    # Check if JWT_SECRET_KEY is already set
    $content = Get-Content $envFile -Raw
    if ($content -match "JWT_SECRET_KEY\s*=") {
        Write-Host "✓ JWT_SECRET_KEY already configured" -ForegroundColor Green
        $jwtSecretKey = ($content | Select-String -Pattern "JWT_SECRET_KEY\s*=\s*(.+)" | ForEach-Object { $_.Matches.Groups[1].Value }).Trim()
        
        if ($jwtSecretKey -eq "your-secret-key-change-in-production" -or $jwtSecretKey -eq "") {
            Write-Host "⚠ JWT_SECRET_KEY is set to default value" -ForegroundColor Yellow
            Write-Host "  Generating a new secure key..." -ForegroundColor Yellow
            
            # Generate secure key
            $jwtSecretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
            
            # Update .env file
            $content = $content -replace "JWT_SECRET_KEY\s*=.*", "JWT_SECRET_KEY=$jwtSecretKey"
            Set-Content -Path $envFile -Value $content
            Write-Host "✓ Generated and saved new JWT_SECRET_KEY" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠ JWT_SECRET_KEY not found in .env" -ForegroundColor Yellow
        Write-Host "  Generating a new secure key..." -ForegroundColor Yellow
        
        # Generate secure key
        $jwtSecretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
        
        # Append to .env file
        Add-Content -Path $envFile -Value "`n# Authentication Configuration"
        Add-Content -Path $envFile -Value "JWT_SECRET_KEY=$jwtSecretKey"
        Add-Content -Path $envFile -Value "JWT_EXPIRATION_HOURS=24"
        Write-Host "✓ Added JWT_SECRET_KEY to .env file" -ForegroundColor Green
    }
} else {
    Write-Host "`n⚠ .env file not found" -ForegroundColor Yellow
    Write-Host "  Creating .env file with authentication configuration..." -ForegroundColor Yellow
    
    # Generate secure key
    $jwtSecretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    # Create .env file
    @"
# Authentication Configuration
JWT_SECRET_KEY=$jwtSecretKey
JWT_EXPIRATION_HOURS=24

# LLM Provider Configuration (set at least one)
# OPENAI_API_KEY=your-openai-api-key
# GEMINI_API_KEY=your-gemini-api-key
# DEEPSEEK_API_KEY=your-deepseek-api-key

# Memory Management (Optional)
USE_PERSISTENT_MEMORY=true
MEMORY_DB_PATH=data/chatbot_memory.db
MAX_CONTEXT_MESSAGES=50
"@ | Out-File -FilePath $envFile -Encoding utf8
    
    Write-Host "✓ Created .env file with JWT_SECRET_KEY" -ForegroundColor Green
}

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file and add your LLM API keys" -ForegroundColor Gray
Write-Host "2. Create a user account: python scripts/create_user.py --username admin --email admin@example.com --password yourpassword" -ForegroundColor Gray
Write-Host "3. Start the application: python app.py" -ForegroundColor Gray
