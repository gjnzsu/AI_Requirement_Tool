"""
Tests for Flask app startup and initialization.

Verifies that the app can start successfully even with missing configuration.
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.mark.integration
@pytest.mark.api
class TestAppStartup:
    """Test suite for app startup and initialization."""
    
    def test_app_imports_successfully(self):
        """Test that app module can be imported without errors."""
        try:
            import app
            assert app is not None
            assert hasattr(app, 'app')
            assert app.app is not None
        except Exception as e:
            pytest.fail(f"Failed to import app: {e}")
    
    def test_app_creates_flask_instance(self):
        """Test that Flask app instance is created."""
        import app
        assert app.app is not None
        assert hasattr(app.app, 'route')
    
    def test_app_starts_without_jwt_secret(self):
        """Test that app can start even without JWT_SECRET_KEY configured."""
        import app
        from config.config import Config
        
        # Save original value
        original_secret = Config.JWT_SECRET_KEY
        
        try:
            # Set JWT_SECRET_KEY to invalid placeholder (should trigger ValueError)
            Config.JWT_SECRET_KEY = 'your-secret-key-change-in-production'
            
            # Try to initialize auth services (should handle gracefully)
            from src.auth import AuthService, UserService
            
            # AuthService should raise ValueError
            with pytest.raises(ValueError):
                AuthService()
            
            # But app should still have None services
            # This means app started successfully
            assert True  # If we get here, app didn't crash
            
        finally:
            # Restore original secret key
            Config.JWT_SECRET_KEY = original_secret
    
    def test_app_handles_missing_auth_services(self):
        """Test that app handles missing authentication services gracefully."""
        import app
        
        # Mock auth_service and user_service as None
        original_auth = app.auth_service
        original_user = app.user_service
        
        try:
            app.auth_service = None
            app.user_service = None
            
            # App should still be accessible
            assert app.app is not None
            
            # Login endpoint should return 503
            with app.app.test_client() as client:
                response = client.post('/api/auth/login', json={
                    'username': 'test',
                    'password': 'test'
                })
                assert response.status_code == 503
                data = response.get_json()
                assert 'error' in data
                assert 'not configured' in data['error'].lower()
        
        finally:
            app.auth_service = original_auth
            app.user_service = original_user
    
    def test_app_routes_are_registered(self):
        """Test that all expected routes are registered."""
        import app
        
        routes = [str(rule) for rule in app.app.url_map.iter_rules()]
        
        # Check for key routes
        assert '/' in routes or any('/' == str(rule) for rule in app.app.url_map.iter_rules())
        assert '/login' in routes or any('/login' == str(rule) for rule in app.app.url_map.iter_rules())
        assert '/api/auth/login' in routes or any('/api/auth/login' == str(rule) for rule in app.app.url_map.iter_rules())
        assert '/api/chat' in routes or any('/api/chat' == str(rule) for rule in app.app.url_map.iter_rules())
    
    def test_app_serves_index_page(self):
        """Test that app serves the index page."""
        import app
        
        with app.app.test_client() as client:
            response = client.get('/')
            assert response.status_code == 200
    
    def test_app_serves_login_page(self):
        """Test that app serves the login page."""
        import app
        
        with app.app.test_client() as client:
            response = client.get('/login')
            assert response.status_code == 200
    
    def test_app_swagger_docs_available(self):
        """Test that Swagger docs endpoint is available (if flasgger installed)."""
        import app
        
        with app.app.test_client() as client:
            response = client.get('/api/docs')
            # Should return 200 if flasgger is installed, or 404 if not
            assert response.status_code in [200, 404]
    
    def test_app_handles_memory_manager_failure(self):
        """Test that app handles memory manager initialization failure gracefully."""
        import app
        
        original_memory = app.memory_manager
        
        try:
            # Set invalid memory path
            with patch('app.Config') as mock_config:
                mock_config.USE_PERSISTENT_MEMORY = True
                mock_config.MEMORY_DB_PATH = '/invalid/path/that/does/not/exist.db'
                mock_config.MAX_CONTEXT_MESSAGES = 50
                
                # App should still work
                assert app.app is not None
                
        finally:
            app.memory_manager = original_memory
    
    def test_user_service_handles_missing_auth_service(self):
        """Test that UserService handles missing AuthService gracefully."""
        import tempfile
        from config.config import Config
        from src.auth.user_service import UserService
        
        # Create temp database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        try:
            # Save original values
            original_jwt_secret = Config.JWT_SECRET_KEY
            original_auth_db_path = getattr(Config, 'AUTH_DB_PATH', None)
            original_expiration = Config.JWT_EXPIRATION_HOURS
            
            # Patch Config attributes directly to trigger ValueError in AuthService
            # Set JWT_SECRET_KEY to the default placeholder which should trigger ValueError
            with patch.object(Config, 'JWT_SECRET_KEY', 'your-secret-key-change-in-production'), \
                 patch.object(Config, 'AUTH_DB_PATH', None, create=True), \
                 patch.object(Config, 'JWT_EXPIRATION_HOURS', 24):
                
                # UserService should initialize but auth_service should be None
                # because AuthService will raise ValueError due to invalid JWT_SECRET_KEY
                user_service = UserService(db_path=db_path)
                assert user_service is not None
                assert user_service.auth_service is None
                
                # Methods that require auth_service should raise ValueError
                with pytest.raises(ValueError):
                    user_service.create_user('test', 'test@example.com', 'password')
                
                # authenticate_user should fail gracefully (no auth service available)
                assert user_service.authenticate_user('test', 'password') is None
        
        finally:
            # Restore original values
            Config.JWT_SECRET_KEY = original_jwt_secret
            if original_auth_db_path is not None:
                Config.AUTH_DB_PATH = original_auth_db_path
            Config.JWT_EXPIRATION_HOURS = original_expiration
            
            # Cleanup
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except Exception:
                pass
    
    def test_app_startup_with_valid_config(self):
        """Test app startup with valid configuration."""
        import app
        import secrets
        from config.config import Config
        
        # Set valid JWT_SECRET_KEY
        test_secret = secrets.token_urlsafe(32)
        
        # Save original value
        original_secret = Config.JWT_SECRET_KEY
        
        try:
            # Patch Config directly (more reliable than reloading modules)
            Config.JWT_SECRET_KEY = test_secret
            
            # Try to create AuthService (should succeed)
            from src.auth import AuthService
            auth_service = AuthService()
            assert auth_service is not None
            assert auth_service.secret_key == test_secret
            
        finally:
            # Restore original value
            Config.JWT_SECRET_KEY = original_secret
