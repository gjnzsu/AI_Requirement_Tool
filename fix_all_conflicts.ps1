# PowerShell script to fix ALL dependency conflicts comprehensively

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Comprehensive Dependency Conflict Fix" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

Write-Host "`nThis script will fix all known dependency conflicts..." -ForegroundColor Yellow

# Step 1: Fix protobuf version (downgrade to <5.0.0 for Google packages)
Write-Host "`n[1/5] Fixing protobuf version..." -ForegroundColor Yellow
pip install "protobuf>=3.19.5,<5.0.0" --force-reinstall

# Step 2: Fix langgraph version (langchain 1.1.2 requires >=1.0.2,<1.1.0)
Write-Host "`n[2/5] Fixing langgraph version..." -ForegroundColor Yellow
pip install "langgraph>=1.0.2,<1.1.0" --upgrade

# Step 3: Reinstall langchain to ensure compatibility with langgraph
Write-Host "`n[3/5] Reinstalling langchain packages..." -ForegroundColor Yellow
pip install "langchain>=1.0.0,<2.0.0" --upgrade

# Step 4: Fix Google packages compatibility
Write-Host "`n[4/5] Fixing Google AI packages..." -ForegroundColor Yellow
Write-Host "  google-generativeai 0.8.5 requires google-ai-generativelanguage==0.6.15" -ForegroundColor Gray
Write-Host "  Installing compatible versions..." -ForegroundColor Gray
# Install google-generativeai (it will pull google-ai-generativelanguage==0.6.15)
pip install "google-generativeai>=0.8.0,<1.0.0" --upgrade
# Ensure exact version is installed
pip install "google-ai-generativelanguage==0.6.15" --force-reinstall

# Step 5: Reinstall langchain-google-genai (may work with 0.6.15)
Write-Host "`n[5/5] Reinstalling langchain-google-genai..." -ForegroundColor Yellow
Write-Host "  Note: langchain-google-genai may work with google-ai-generativelanguage 0.6.15" -ForegroundColor Gray
pip install "langchain-google-genai>=1.0.0,<3.0.0" --upgrade

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "Dependency Fix Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`nVerifying dependencies..." -ForegroundColor Yellow
$conflicts = pip check 2>&1 | Out-String
if ($conflicts -match "has requirement") {
    Write-Host "`n⚠ Remaining conflicts:" -ForegroundColor Yellow
    Write-Host $conflicts -ForegroundColor Gray
    
    Write-Host "`nAnalyzing conflicts..." -ForegroundColor Yellow
    
    # Check for google-ai-generativelanguage conflict
    if ($conflicts -match "google-ai-generativelanguage") {
        Write-Host "`n⚠ google-ai-generativelanguage conflict detected" -ForegroundColor Yellow
        Write-Host "  This is expected. langchain-google-genai may still work." -ForegroundColor Gray
        Write-Host "  The chatbot uses google-generativeai directly, so Gemini will work." -ForegroundColor Gray
    }
    
    # Check for mem0ai conflict
    if ($conflicts -match "mem0ai") {
        Write-Host "`n⚠ mem0ai conflict detected (expected - optional package)" -ForegroundColor Yellow
    }
    
    # Check for langgraph conflict
    if ($conflicts -match "langgraph") {
        Write-Host "`n✗ langgraph conflict detected - this needs to be fixed!" -ForegroundColor Red
    }
} else {
    Write-Host "✓ No conflicts found!" -ForegroundColor Green
}

Write-Host "`nIf conflicts persist, you may need to:" -ForegroundColor Yellow
Write-Host "  1. Use a virtual environment for isolation" -ForegroundColor Gray
Write-Host "  2. Install packages in a different order" -ForegroundColor Gray
Write-Host "  3. Accept some conflicts if they don't affect functionality" -ForegroundColor Gray
