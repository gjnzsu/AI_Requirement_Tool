# PowerShell script to fix existing dependency conflicts

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Fixing Dependency Conflicts" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

Write-Host "`nThis script will fix protobuf and google-ai-generativelanguage conflicts..." -ForegroundColor Yellow

# Step 1: Fix protobuf version (downgrade to <5.0.0)
Write-Host "`n[1/3] Fixing protobuf version..." -ForegroundColor Yellow
pip install "protobuf>=3.19.5,<5.0.0" --force-reinstall --no-deps
pip install "protobuf>=3.19.5,<5.0.0"

# Step 2: Fix langgraph version (langchain 1.1.2 requires >=1.0.2,<1.1.0)
Write-Host "`n[2/4] Fixing langgraph version..." -ForegroundColor Yellow
pip install "langgraph>=1.0.2,<1.1.0" --upgrade

# Step 3: Fix google-ai-generativelanguage version
Write-Host "`n[3/4] Fixing google-ai-generativelanguage version..." -ForegroundColor Yellow
# Try to upgrade, but may conflict with google-generativeai
pip install "google-ai-generativelanguage>=0.6.15" --upgrade

# Step 4: Reinstall langchain packages to ensure compatibility
Write-Host "`n[4/4] Reinstalling langchain packages..." -ForegroundColor Yellow
pip install "langchain>=1.0.0,<2.0.0" "langchain-google-genai>=1.0.0,<3.0.0" --upgrade

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "Dependency Fix Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`nVerifying dependencies..." -ForegroundColor Yellow
pip check

Write-Host "`nNote: If mem0ai conflicts appear, that's expected." -ForegroundColor Yellow
Write-Host "mem0ai is optional and has protobuf conflicts with Google packages." -ForegroundColor Gray
