#!/bin/bash
# Bash script to install requirements in stages to avoid dependency resolution issues

echo "======================================================================"
echo "Installing Chatbot Dependencies (Staged Installation)"
echo "======================================================================"

# Step 1: Upgrade pip first
echo ""
echo "[1/8] Upgrading pip..."
python -m pip install --upgrade pip

# Step 2: Install core dependencies first
echo ""
echo "[2/8] Installing core dependencies..."
pip install "jira>=3.5.2,<4.0.0" "openai>=1.12.0,<2.0.0" "python-dotenv>=1.0.0,<2.0.0" "requests>=2.26.0,<3.0.0"

# Step 3: Install protobuf FIRST (before Google packages) - critical for compatibility
echo ""
echo "[3/8] Installing protobuf (compatible version for Google packages)..."
pip install "protobuf>=3.19.5,<5.0.0"

# Step 4: Install Google packages (requires protobuf<5.0.0)
echo ""
echo "[4/8] Installing Google AI packages..."
pip install "google-generativeai>=0.3.0,<1.0.0" "google-ai-generativelanguage>=0.9.0,<1.0.0"

# Step 5: Install Flask and web dependencies
echo ""
echo "[5/8] Installing Flask and web dependencies..."
pip install "Flask>=2.0.1,<4.0.0" "flask-cors>=3.1.0,<5.0.0" "flasgger>=0.9.7,<1.0.0"

# Step 6: Install authentication dependencies
echo ""
echo "[6/8] Installing authentication dependencies..."
pip install "PyJWT>=2.8.0,<3.0.0" "bcrypt>=4.0.0,<5.0.0"

# Step 7: Install LangChain and AI dependencies (these can be heavy)
echo ""
echo "[7/8] Installing LangChain and AI dependencies..."
echo "This may take a while due to large dependencies..."
pip install "langchain>=1.0.0,<2.0.0" "langchain-openai>=1.0.0,<2.0.0" "langchain-google-genai>=1.0.0,<3.0.0" "langchain-core>=1.0.0,<2.0.0"
pip install "langgraph>=0.2.0,<1.0.0"
pip install "transformers>=4.11.3,<5.0.0" "numpy>=1.21.2,<2.0.0"

# Step 8: Install remaining dependencies
echo ""
echo "[8/8] Installing remaining dependencies..."
pip install "PyPDF2>=3.0.0,<4.0.0" "mcp>=0.9.0,<1.0.0"

echo ""
echo "======================================================================"
echo "Installation Complete!"
echo "======================================================================"
echo ""
echo "Important Notes:"
echo "  - mem0ai is NOT installed due to protobuf conflicts with Google packages"
echo "  - If you need mem0ai, install separately: pip install mem0ai --no-deps"
echo "  - PyTorch is NOT installed by default"
echo ""
echo "If needed, install PyTorch separately:"
echo "  pip install torch"
