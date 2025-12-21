# PowerShell script to install langchain-google-genai with conflict resolution

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Installing langchain-google-genai (with conflict resolution)" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

Write-Host "`nNote: This may conflict with google-ai-generativelanguage version." -ForegroundColor Yellow
Write-Host "google-generativeai 0.8.5 requires google-ai-generativelanguage==0.6.15" -ForegroundColor Gray
Write-Host "langchain-google-genai may work with this version or need >=0.9.0" -ForegroundColor Gray

# Step 1: Ensure google-generativeai is installed
Write-Host "`n[1/3] Ensuring google-generativeai is installed..." -ForegroundColor Yellow
pip install "google-generativeai>=0.8.0,<1.0.0"

# Step 2: Install langchain-google-genai
Write-Host "`n[2/3] Installing langchain-google-genai..." -ForegroundColor Yellow
pip install "langchain-google-genai>=1.0.0,<3.0.0"

# Step 3: Test import
Write-Host "`n[3/3] Testing import..." -ForegroundColor Yellow
python -c "try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print('✓ langchain-google-genai imported successfully')
except ImportError as e:
    print(f'✗ Import failed: {e}')
    print('  The chatbot will still work with Gemini using direct google-generativeai integration.')
except Exception as e:
    print(f'⚠ Import warning: {e}')
    print('  May still work, test functionality to verify.')
"

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green

Write-Host "`nNote: If there are version conflicts, the chatbot will use" -ForegroundColor Yellow
Write-Host "direct google-generativeai integration (already implemented)." -ForegroundColor Gray
