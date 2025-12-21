# PowerShell script to install requirements in stages to avoid dependency resolution issues

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Installing Chatbot Dependencies (Staged Installation)" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

# Step 1: Upgrade pip first
Write-Host "`n[1/8] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Step 2: Install core dependencies first (without Google packages)
Write-Host "`n[2/8] Installing core dependencies..." -ForegroundColor Yellow
pip install "jira>=3.5.2,<4.0.0" "openai>=1.12.0,<2.0.0" "python-dotenv>=1.0.0,<2.0.0" "requests>=2.26.0,<3.0.0"

# Step 3: Install protobuf FIRST (before Google packages) - CRITICAL for compatibility
Write-Host "`n[3/8] Installing protobuf (compatible version for Google packages)..." -ForegroundColor Yellow
pip install "protobuf>=3.19.5,<5.0.0"

# Step 4: Install Google packages (requires protobuf<5.0.0)
Write-Host "`n[4/8] Installing Google AI packages..." -ForegroundColor Yellow
# Install google-generativeai first (it will pull compatible google-ai-generativelanguage)
pip install "google-generativeai>=0.8.0,<1.0.0"
# Then upgrade google-ai-generativelanguage if needed for langchain-google-genai
pip install "google-ai-generativelanguage>=0.6.15" --upgrade

# Step 5: Install Flask and web dependencies
Write-Host "`n[5/8] Installing Flask and web dependencies..." -ForegroundColor Yellow
pip install "Flask>=2.0.1,<4.0.0" "flask-cors>=3.1.0,<5.0.0" "flasgger>=0.9.7,<1.0.0"

# Step 6: Install authentication dependencies
Write-Host "`n[6/8] Installing authentication dependencies..." -ForegroundColor Yellow
pip install "PyJWT>=2.8.0,<3.0.0" "bcrypt>=4.0.0,<5.0.0"

# Step 7: Install LangChain and AI dependencies (these can be heavy)
Write-Host "`n[7/8] Installing LangChain and AI dependencies..." -ForegroundColor Yellow
Write-Host "This may take a while due to large dependencies..." -ForegroundColor Gray
# Install langgraph first (langchain 1.1.2 requires langgraph>=1.0.2,<1.1.0)
pip install "langgraph>=1.0.2,<1.1.0"
# Then install langchain packages
pip install "langchain>=1.0.0,<2.0.0" "langchain-openai>=1.0.0,<2.0.0" "langchain-core>=1.0.0,<2.0.0"
# langchain-google-genai is optional - install separately if needed (may have version conflicts)
Write-Host "  Note: langchain-google-genai skipped due to potential version conflicts" -ForegroundColor Gray
Write-Host "  Install separately if needed: pip install langchain-google-genai" -ForegroundColor Gray
pip install "transformers>=4.11.3,<5.0.0" "numpy>=1.21.2,<2.0.0"

# Step 8: Install remaining dependencies
Write-Host "`n[8/8] Installing remaining dependencies..." -ForegroundColor Yellow
pip install "PyPDF2>=3.0.0,<4.0.0" "mcp>=0.9.0,<1.0.0"

Write-Host "`n" + "=" * 70 -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Green
Write-Host "`nImportant Notes:" -ForegroundColor Yellow
Write-Host "  - mem0ai is NOT installed due to protobuf conflicts with Google packages" -ForegroundColor Gray
Write-Host "  - If you need mem0ai, install separately: pip install mem0ai --no-deps" -ForegroundColor Gray
Write-Host "  - PyTorch is NOT installed by default" -ForegroundColor Gray
Write-Host "`nIf needed, install PyTorch separately:" -ForegroundColor Yellow
Write-Host "  Windows CPU: pip install torch --index-url https://download.pytorch.org/whl/cpu" -ForegroundColor Gray
Write-Host "  Windows GPU: pip install torch --index-url https://download.pytorch.org/whl/cu118" -ForegroundColor Gray
