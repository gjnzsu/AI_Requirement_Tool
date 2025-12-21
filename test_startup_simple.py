#!/usr/bin/env python3
"""
Simplified startup test to identify specific import failures.

Run this to see exactly what's failing:
    python test_startup_simple.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("Simple Startup Diagnostic")
print("=" * 70)

# Test 1: Basic Python
print("\n[1] Testing Python basics...")
try:
    import json
    import os
    from datetime import datetime
    print("✓ Basic imports OK")
except Exception as e:
    print(f"✗ Basic imports failed: {e}")
    sys.exit(1)

# Test 2: Flask
print("\n[2] Testing Flask...")
try:
    from flask import Flask
    print("✓ Flask imported")
except ImportError as e:
    print(f"✗ Flask not installed: {e}")
    print("  Install with: pip install Flask")
    sys.exit(1)

# Test 3: flask-cors
print("\n[3] Testing flask-cors...")
try:
    from flask_cors import CORS
    print("✓ flask-cors imported")
except ImportError as e:
    print(f"✗ flask-cors not installed: {e}")
    print("  Install with: pip install flask-cors")
    sys.exit(1)

# Test 4: Config
print("\n[4] Testing config...")
try:
    from config.config import Config
    print("✓ Config imported")
    print(f"  JWT_SECRET_KEY: {'Set' if Config.JWT_SECRET_KEY and Config.JWT_SECRET_KEY != 'your-secret-key-change-in-production' else 'Not set'}")
except Exception as e:
    print(f"✗ Config import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Logger
print("\n[5] Testing logger...")
try:
    from src.utils.logger import get_logger
    logger = get_logger('test')
    print("✓ Logger imported")
except Exception as e:
    print(f"✗ Logger import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Auth Service
print("\n[6] Testing AuthService...")
try:
    from src.auth.auth_service import AuthService
    print("✓ AuthService class imported")
    
    # Try to instantiate (might fail if JWT_SECRET_KEY not set)
    try:
        auth_service = AuthService()
        print("✓ AuthService instantiated")
    except ValueError as e:
        print(f"⚠ AuthService instantiation failed (expected): {e}")
except Exception as e:
    print(f"✗ AuthService import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 7: User Service
print("\n[7] Testing UserService...")
try:
    from src.auth.user_service import UserService
    print("✓ UserService class imported")
    
    # Try to instantiate with temp DB
    import tempfile
    fd, db_path = tempfile.mkstemp(suffix='.db')
    import os
    os.close(fd)
    
    try:
        user_service = UserService(db_path=db_path)
        print("✓ UserService instantiated")
        if user_service.auth_service is None:
            print("  (AuthService is None - expected if JWT_SECRET_KEY not set)")
    except Exception as e:
        print(f"⚠ UserService instantiation failed: {e}")
    finally:
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except:
            pass
except Exception as e:
    print(f"✗ UserService import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 8: Auth module
print("\n[8] Testing auth module...")
try:
    from src.auth import AuthService, UserService, token_required, get_current_user
    print("✓ Auth module imported")
except Exception as e:
    print(f"✗ Auth module import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 9: Memory Manager
print("\n[9] Testing MemoryManager...")
try:
    from src.services.memory_manager import MemoryManager
    print("✓ MemoryManager imported")
except Exception as e:
    print(f"✗ MemoryManager import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 10: Chatbot
print("\n[10] Testing Chatbot...")
try:
    from src.chatbot import Chatbot
    print("✓ Chatbot imported")
except Exception as e:
    print(f"✗ Chatbot import failed: {e}")
    import traceback
    traceback.print_exc()

# Test 11: App module (the critical one)
print("\n[11] Testing app module import...")
try:
    import app
    print("✓ App module imported")
    
    if hasattr(app, 'app'):
        print("✓ Flask app instance exists")
        print(f"  App type: {type(app.app)}")
    else:
        print("✗ Flask app instance not found")
        
except ImportError as e:
    print(f"✗ App import failed (ImportError): {e}")
    print("  This usually means a dependency is missing")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"✗ App import failed: {e}")
    print(f"  Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 12: Flask app functionality
print("\n[12] Testing Flask app functionality...")
try:
    import app
    
    if hasattr(app, 'app') and app.app is not None:
        flask_app = app.app
        
        # Test routes
        routes = list(flask_app.url_map.iter_rules())
        print(f"✓ Found {len(routes)} routes")
        
        # Test test client
        flask_app.config['TESTING'] = True
        with flask_app.test_client() as client:
            response = client.get('/')
            print(f"✓ Index route works (status: {response.status_code})")
    else:
        print("✗ Flask app instance not available")
        
except Exception as e:
    print(f"✗ Flask app test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Diagnostic Complete!")
print("=" * 70)
print("\nIf all tests passed, the app should start successfully.")
print("Run: python app.py")
