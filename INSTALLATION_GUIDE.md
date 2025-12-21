# Installation Guide - Resolving Dependency Issues

## Problem

When installing `requirements.txt`, you may encounter:
```
error: resolution-too-deep
× Dependency resolution exceeded maximum depth
```

This happens because pip's dependency resolver struggles with complex dependency graphs, especially with packages like LangChain, Transformers, and their dependencies.

## Solutions

### Option 1: Staged Installation (Recommended)

Use the provided installation scripts that install dependencies in stages:

**Windows PowerShell:**
```powershell
.\install_requirements.ps1
```

**Linux/Mac:**
```bash
chmod +x install_requirements.sh
./install_requirements.sh
```

### Option 2: Manual Staged Installation

Install dependencies in groups:

```bash
# 1. Upgrade pip first
python -m pip install --upgrade pip

# 2. Core dependencies
pip install "jira>=3.5.2,<4.0.0" "openai>=1.12.0,<2.0.0" "google-generativeai>=0.3.0,<1.0.0" "python-dotenv>=1.0.0,<2.0.0" "requests>=2.26.0,<3.0.0"

# 3. Flask and web
pip install "Flask>=2.0.1,<4.0.0" "flask-cors>=3.1.0,<5.0.0" "flasgger>=0.9.7,<1.0.0"

# 4. Authentication
pip install "PyJWT>=2.8.0,<3.0.0" "bcrypt>=4.0.0,<5.0.0"

# 5. LangChain (install separately)
pip install "langchain>=1.0.0,<2.0.0" "langchain-openai>=1.0.0,<2.0.0" "langchain-google-genai>=1.0.0,<2.0.0" "langchain-core>=1.0.0,<2.0.0"
pip install "langgraph>=0.2.0,<1.0.0"

# 6. Transformers and ML libraries
pip install "transformers>=4.11.3,<5.0.0" "numpy>=1.21.2,<2.0.0"

# 7. Remaining dependencies
pip install "PyPDF2>=3.0.0,<4.0.0" "mcp>=0.9.0,<1.0.0" "mem0ai>=1.0.0,<2.0.0"
```

### Option 3: Use pip-tools (Alternative)

If you have `pip-tools` installed:

```bash
# Install pip-tools
pip install pip-tools

# Compile requirements (this resolves dependencies)
pip-compile requirements.txt

# Install from compiled file
pip-sync requirements.txt
```

### Option 4: Use Virtual Environment (Always Recommended)

Create a fresh virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Then use Option 1 or 2 above
```

## What Changed

The `requirements.txt` file has been updated with:
- **Upper bounds** added to all packages (e.g., `>=1.0.0,<2.0.0`)
- This constrains the dependency resolver and prevents it from exploring too many version combinations

## Troubleshooting

### If installation still fails:

1. **Upgrade pip:**
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Clear pip cache:**
   ```bash
   pip cache purge
   ```

3. **Install without cache:**
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

4. **Use specific Python version:**
   Ensure you're using Python 3.8+ (recommended: Python 3.10 or 3.11)

5. **Install problematic packages separately:**
   If a specific package fails, install it individually:
   ```bash
   pip install <package-name>
   ```

### Common Issues

**Issue: `transformers` conflicts**
- Solution: Install transformers separately after other packages

**Issue: `langchain` conflicts**
- Solution: Install langchain packages in order (core first, then providers)

**Issue: Memory errors during installation**
- Solution: Install packages one at a time or use `--no-cache-dir`

## Minimal Installation (For Testing Only)

If you only need basic functionality:

```bash
pip install Flask flask-cors PyJWT bcrypt flasgger python-dotenv requests
```

Then install other packages as needed.

## Verification

After installation, verify packages are installed:

```bash
python -c "import flask, jwt, bcrypt, flasgger; print('Core packages OK')"
```

## Next Steps

1. Install dependencies using one of the options above
2. Set up your `.env` file with API keys
3. Run the application: `python app.py`
4. Access Swagger docs: `http://localhost:5000/api/docs`
