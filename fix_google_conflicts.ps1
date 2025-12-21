# PowerShell script to fix Google package conflicts specifically

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Fixing Google AI Package Conflicts" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

Write-Host "`nIssue: google-generativeai 0.8.5 requires google-ai-generativelanguage==0.6.15" -ForegroundColor Yellow
Write-Host "But langchain-google-genai may need a newer version." -ForegroundColor Yellow
Write-Host "`nStrategy: Install compatible versions..." -ForegroundColor Yellow

# Option 1: Try to use newer google-generativeai that supports newer google-ai-generativelanguage
Write-Host "`n[1/3] Attempting to upgrade google-generativeai..." -ForegroundColor Yellow
pip install "google-generativeai>=0.8.0" --upgrade

# Check what version was installed
$genaiVersion = pip show google-generativeai | Select-String "Version:"
Write-Host "Installed version: $genaiVersion" -ForegroundColor Gray

# Option 2: Install compatible google-ai-generativelanguage
Write-Host "`n[2/3] Installing compatible google-ai-generativelanguage..." -ForegroundColor Yellow
# Try to install the version that google-generativeai needs
pip install "google-ai-generativelanguage==0.6.15" --force-reinstall

# Option 3: Upgrade langchain-google-genai (it may work with older google-ai-generativelanguage)
Write-Host "`n[3/3] Upgrading langchain-google-genai..." -ForegroundColor Yellow
pip install "langchain-google-genai>=1.0.0,<3.0.0" --upgrade

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "Google Package Fix Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`nNote: If conflicts persist, langchain-google-genai may work with" -ForegroundColor Yellow
Write-Host "google-ai-generativelanguage 0.6.15. Test the functionality to verify." -ForegroundColor Gray
