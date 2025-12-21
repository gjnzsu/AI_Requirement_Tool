# Startup Troubleshooting Guide

## Common Startup Errors and Solutions

### Error: "JWT_SECRET_KEY must be set in configuration"

**Problem:** Authentication services require a JWT secret key to be configured.

**Solution:**
1. Create or edit `.env` file in the project root
2. Add the following line:
   ```
   JWT_SECRET_KEY=your-very-secure-secret-key-here
   ```
3. Generate a secure key using:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```
4. Restart the application

**Note:** The application will start even without authentication configured, but authentication endpoints will return 503 errors.

### Error: "ModuleNotFoundError" or Import Errors

**Problem:** Required packages are not installed.

**Solution:**
```bash
# Install dependencies using the staged installation script
.\install_requirements.ps1

# Or install manually
pip install -r requirements.txt
```

### Error: "Port 5000 already in use"

**Problem:** Another application is using port 5000.

**Solution:**
1. Find and stop the process using port 5000:
   ```powershell
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```
2. Or change the port in `app.py`:
   ```python
   app.run(debug=True, host='0.0.0.0', port=5001)  # Change 5000 to 5001
   ```

### Error: Database initialization errors

**Problem:** SQLite database cannot be created or accessed.

**Solution:**
1. Ensure the `data/` directory exists and is writable
2. Check file permissions
3. Verify disk space is available

### Error: "Authentication services not initialized"

**Problem:** Authentication services failed to initialize (usually due to missing JWT_SECRET_KEY).

**Solution:**
- This is a warning, not a fatal error
- The application will still start
- Set `JWT_SECRET_KEY` in `.env` to enable authentication
- See error above for details

## Quick Start Checklist

Before starting the application:

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with at least:
  - [ ] `JWT_SECRET_KEY` (for authentication)
  - [ ] `OPENAI_API_KEY` or other LLM provider keys (for chatbot)
- [ ] Port 5000 is available
- [ ] `data/` directory exists and is writable

## Minimal .env File

Create a `.env` file with at minimum:

```env
# Authentication (Required for auth features)
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_EXPIRATION_HOURS=24

# LLM Provider (At least one required for chatbot)
OPENAI_API_KEY=your-openai-api-key
# OR
GEMINI_API_KEY=your-gemini-api-key
# OR
DEEPSEEK_API_KEY=your-deepseek-api-key

# Optional: Memory Management
USE_PERSISTENT_MEMORY=true
MEMORY_DB_PATH=data/chatbot_memory.db
```

## Testing the Installation

Run this to verify everything is set up:

```python
python -c "
import sys
sys.path.insert(0, '.')
try:
    from config.config import Config
    from src.auth import AuthService, UserService
    print('✓ Config loaded')
    print('✓ Auth services imported')
    print('✓ Setup looks good!')
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
"
```

## Getting Help

If you encounter other errors:

1. Check the full error traceback
2. Verify all dependencies are installed
3. Check `.env` file configuration
4. Ensure Python version is 3.8+
5. Try running in a fresh virtual environment
