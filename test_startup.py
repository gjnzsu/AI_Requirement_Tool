#!/usr/bin/env python3
"""
Quick startup test script to verify the Flask app can start successfully.

Run this to diagnose startup issues:
    python test_startup.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported."""
    print("=" * 70)
    print("Testing Imports")
    print("=" * 70)
    
    import_success = True
    
    # Test Flask
    try:
        print("✓ Importing Flask...")
        from flask import Flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Flask: {e}")
        print("  Install with: pip install Flask")
        import_success = False
    
    # Test flask-cors
    try:
        print("✓ Importing flask-cors...")
        from flask_cors import CORS
        print("✓ flask-cors imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import flask-cors: {e}")
        print("  Install with: pip install flask-cors")
        import_success = False
    
    # Test config
    try:
        print("✓ Importing config...")
        from config.config import Config
        print("✓ Config imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Config: {e}")
        import traceback
        traceback.print_exc()
        import_success = False
    
    # Test auth modules (optional - might fail if JWT_SECRET_KEY not set)
    try:
        print("✓ Testing auth imports...")
        from src.auth import AuthService, UserService
        print("✓ Auth modules imported successfully")
    except ImportError as e:
        print(f"⚠ Auth modules import failed: {e}")
        print("  This might be due to missing dependencies (PyJWT, bcrypt)")
    except Exception as e:
        print(f"⚠ Auth modules import warning: {e}")
        print("  This is expected if JWT_SECRET_KEY is not set")
    
    # Test app import (this is the critical one)
    try:
        print("✓ Importing app module...")
        import app
        print("✓ App module imported successfully")
        
        # Check if Flask app was created
        if hasattr(app, 'app') and app.app is not None:
            print("✓ Flask app instance created successfully")
        else:
            print("⚠ Flask app instance not found (might be an issue)")
            import_success = False
            
    except ImportError as e:
        print(f"✗ Failed to import app (ImportError): {e}")
        print("  This usually means a required package is missing.")
        print("  Try: pip install Flask flask-cors PyJWT bcrypt")
        import traceback
        traceback.print_exc()
        import_success = False
    except ValueError as e:
        print(f"⚠ App imported but with warnings: {e}")
        print("  This is expected if JWT_SECRET_KEY is not set")
        print("✓ App imported successfully (with warnings)")
        # Still consider this a success
    except Exception as e:
        print(f"✗ Failed to import app: {e}")
        print("  Error type:", type(e).__name__)
        import traceback
        traceback.print_exc()
        import_success = False
    
    return import_success

def test_auth_services():
    """Test authentication services initialization."""
    print("\n" + "=" * 70)
    print("Testing Authentication Services")
    print("=" * 70)
    
    from config.config import Config
    
    # Check JWT_SECRET_KEY
    jwt_secret = Config.JWT_SECRET_KEY
    print(f"JWT_SECRET_KEY: {'Set' if jwt_secret and jwt_secret != 'your-secret-key-change-in-production' else 'Not set (using default)'}")
    
    try:
        from src.auth import AuthService
        auth_service = AuthService()
        print("✓ AuthService initialized successfully")
        return True
    except ValueError as e:
        print(f"⚠ AuthService initialization warning: {e}")
        print("  This is expected if JWT_SECRET_KEY is not set")
        return False
    except Exception as e:
        print(f"✗ AuthService initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_service():
    """Test user service initialization."""
    print("\n" + "=" * 70)
    print("Testing User Service")
    print("=" * 70)
    
    try:
        from src.auth import UserService
        import tempfile
        
        # Create temp database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            user_service = UserService(db_path=db_path)
            print("✓ UserService initialized successfully")
            
            if user_service.auth_service is None:
                print("⚠ AuthService is None (expected if JWT_SECRET_KEY not set)")
            else:
                print("✓ AuthService is available")
            
            return True
        finally:
            # Cleanup
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except Exception:
                pass
    except Exception as e:
        print(f"✗ UserService initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flask_app():
    """Test Flask app creation."""
    print("\n" + "=" * 70)
    print("Testing Flask App")
    print("=" * 70)
    
    try:
        # Try to import app (might have been imported already)
        try:
            import app
        except Exception:
            # If import failed, try again with better error handling
            print("⚠ App import had issues, trying to reload...")
            import importlib
            if 'app' in sys.modules:
                importlib.reload(sys.modules['app'])
            else:
                import app
        
        # Check if app instance exists
        if not hasattr(app, 'app'):
            print("✗ Flask app instance not found")
            print("  This might indicate an import error during app initialization")
            return False
        
        flask_app = app.app
        
        if flask_app is None:
            print("✗ Flask app instance is None")
            return False
        
        print("✓ Flask app instance found")
        
        # Check if app has routes
        try:
            routes = list(flask_app.url_map.iter_rules())
            print(f"✓ Found {len(routes)} routes")
        except Exception as e:
            print(f"⚠ Could not list routes: {e}")
            print("  But app instance exists, which is good")
        
        # Test app can create test client
        try:
            flask_app.config['TESTING'] = True
            with flask_app.test_client() as client:
                response = client.get('/')
                print(f"✓ Index route responds with status {response.status_code}")
        except Exception as e:
            print(f"⚠ Could not test route: {e}")
            print("  But app instance exists, which is good")
        
        return True
    except AttributeError as e:
        print(f"✗ Flask app attribute error: {e}")
        print("  This might indicate the app module structure is incorrect")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Flask app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all startup tests."""
    print("\n" + "=" * 70)
    print("Flask App Startup Test")
    print("=" * 70)
    print("\nFor more detailed diagnostics, run: python test_startup_simple.py")
    print("=" * 70)
    
    results = []
    
    # Test imports
    import_result = test_imports()
    results.append(("Imports", import_result))
    
    # Only continue if imports succeeded
    if not import_result:
        print("\n⚠ Import test failed. Cannot continue with other tests.")
        print("Run 'python test_startup_simple.py' for detailed diagnostics.")
        return 1
    
    # Test auth services (this might fail if JWT_SECRET_KEY not set - that's OK)
    auth_result = test_auth_services()
    results.append(("Auth Services", auth_result))
    # Don't fail overall if auth fails (it's expected without JWT_SECRET_KEY)
    
    # Test user service
    user_result = test_user_service()
    results.append(("User Service", user_result))
    
    # Test Flask app
    flask_result = test_flask_app()
    results.append(("Flask App", flask_result))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    critical_failed = False
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
        # Only imports and Flask app are critical
        if not result and name in ["Imports", "Flask App"]:
            critical_failed = True
    
    print("\n" + "=" * 70)
    if not critical_failed:
        print("✓ Critical tests passed! App should start successfully.")
        if not all(r for _, r in results):
            print("\n⚠ Some optional tests failed (auth services).")
            print("  This is expected if JWT_SECRET_KEY is not set.")
            print("  The app will start, but authentication will be disabled.")
    else:
        print("✗ Critical tests failed. App may not start properly.")
        print("\nRun 'python test_startup_simple.py' for detailed diagnostics.")
    print("=" * 70)
    
    return 0 if not critical_failed else 1

if __name__ == '__main__':
    sys.exit(main())
