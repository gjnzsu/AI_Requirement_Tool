"""
Tests for authentication API endpoints.

Tests login, token validation, and protected endpoint access.
"""

import pytest
import json
import os
import tempfile
import secrets
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import jwt

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app import app as flask_app
from src.auth.auth_service import AuthService
from src.auth.user_service import UserService


@pytest.fixture(scope="function")
def test_client():
    """Create a Flask test client."""
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def temp_auth_db():
    """Create a temporary database for authentication testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    yield db_path
    
    # Cleanup - remove temp database file
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def auth_setup(temp_auth_db):
    """Set up authentication services with test secret key."""
    from config.config import Config
    
    # Generate a test secret key
    test_secret = secrets.token_urlsafe(32)
    
    # Save original values
    original_secret = Config.JWT_SECRET_KEY
    original_expiration = Config.JWT_EXPIRATION_HOURS
    
    # Patch Config directly (more reliable than reloading modules)
    # This ensures all modules that imported Config will see the new value
    Config.JWT_SECRET_KEY = test_secret
    Config.JWT_EXPIRATION_HOURS = 24
    
    try:
        # Create auth services
        auth_service = AuthService()
        user_service = UserService(db_path=temp_auth_db)
        
        # Create a test user
        test_user = user_service.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        yield auth_service, user_service, test_user, test_secret
    
    finally:
        # Restore original values
        Config.JWT_SECRET_KEY = original_secret
        Config.JWT_EXPIRATION_HOURS = original_expiration


@pytest.mark.integration
@pytest.mark.api
class TestAuthAPI:
    """Test suite for authentication API endpoints."""
    
    def test_login_success(self, test_client, auth_setup):
        """Test successful login returns token and user info."""
        auth_service, user_service, test_user, secret = auth_setup
        
        # Mock auth services in app
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                response = test_client.post(
                    '/api/auth/login',
                    json={
                        'username': 'testuser',
                        'password': 'testpassword123'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                
                # Verify response is JSON
                assert response.is_json
                data = response.get_json()
                
                assert 'token' in data
                assert 'user' in data
                assert data['user']['username'] == 'testuser'
                assert data['user']['email'] == 'test@example.com'
                assert data['user']['id'] == test_user['id']
                
                # Verify token is valid
                token = data['token']
                payload = auth_service.verify_token(token)
                assert payload is not None
                assert payload['user_id'] == test_user['id']
                assert payload['username'] == 'testuser'
    
    def test_login_invalid_username(self, test_client, auth_setup):
        """Test login with invalid username returns 401."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                response = test_client.post(
                    '/api/auth/login',
                    json={
                        'username': 'nonexistent',
                        'password': 'testpassword123'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 401
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'invalid' in data['error'].lower() or 'username' in data['error'].lower()
    
    def test_login_invalid_password(self, test_client, auth_setup):
        """Test login with invalid password returns 401."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                response = test_client.post(
                    '/api/auth/login',
                    json={
                        'username': 'testuser',
                        'password': 'wrongpassword'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 401
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'invalid' in data['error'].lower() or 'password' in data['error'].lower()
    
    def test_login_missing_credentials(self, test_client, auth_setup):
        """Test login with missing credentials returns 400."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                # Missing username
                response = test_client.post(
                    '/api/auth/login',
                    json={'password': 'testpassword123'},
                    content_type='application/json'
                )
                assert response.status_code == 400
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'required' in data['error'].lower()
                
                # Missing password
                response = test_client.post(
                    '/api/auth/login',
                    json={'username': 'testuser'},
                    content_type='application/json'
                )
                assert response.status_code == 400
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'required' in data['error'].lower()
    
    def test_login_invalid_json(self, test_client, auth_setup):
        """Test login with invalid JSON returns proper JSON error (not HTML)."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                # Send invalid JSON
                response = test_client.post(
                    '/api/auth/login',
                    data='invalid json{',
                    content_type='application/json'
                )
                
                # Should return error status (400, 415, or 500)
                assert response.status_code >= 400
                
                # Most importantly: Verify it's JSON (not HTML error page)
                # This is the key fix - ensuring API endpoints always return JSON
                content_type = response.headers.get('Content-Type', '')
                
                # Check if response is JSON (either via Content-Type header or is_json property)
                is_json_response = (
                    'application/json' in content_type or 
                    response.is_json or
                    (response.data and response.data.decode('utf-8', errors='ignore').strip().startswith('{'))
                )
                
                assert is_json_response, f"Expected JSON response but got Content-Type: {content_type}"
                
                # If it's JSON, verify it has error structure
                if is_json_response:
                    try:
                        data = response.get_json()
                        assert 'error' in data or 'message' in data
                    except Exception:
                        # If get_json fails, at least verify it starts with JSON
                        response_text = response.data.decode('utf-8', errors='ignore')
                        assert response_text.strip().startswith('{')
    
    def test_protected_endpoint_without_token(self, test_client, auth_setup):
        """Test accessing protected endpoint without token returns 401."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                response = test_client.get('/api/auth/me')
                
                assert response.status_code == 401
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'authentication' in data['error'].lower() or 'token' in data['error'].lower()
    
    def test_protected_endpoint_with_valid_token(self, test_client, auth_setup):
        """Test accessing protected endpoint with valid token succeeds."""
        auth_service, user_service, test_user, secret = auth_setup
        
        # Generate token
        token = auth_service.generate_token(test_user['id'], test_user['username'])
        
        # Patch both app-level and middleware-level services
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                with patch('src.auth.middleware.auth_service', auth_service):
                    with patch('src.auth.middleware.user_service', user_service):
                        response = test_client.get(
                            '/api/auth/me',
                            headers={'Authorization': f'Bearer {token}'}
                        )
                        
                        assert response.status_code == 200
                        assert response.is_json
                        data = response.get_json()
                        assert 'user' in data
                        assert data['user']['id'] == test_user['id']
                        assert data['user']['username'] == test_user['username']
    
    def test_protected_endpoint_with_invalid_token(self, test_client, auth_setup):
        """Test accessing protected endpoint with invalid token returns 401."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                response = test_client.get(
                    '/api/auth/me',
                    headers={'Authorization': 'Bearer invalid_token_here'}
                )
                
                assert response.status_code == 401
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'invalid' in data['error'].lower() or 'expired' in data['error'].lower()
    
    def test_protected_endpoint_with_expired_token(self, test_client, auth_setup):
        """Test accessing protected endpoint with expired token returns 401."""
        auth_service, user_service, test_user, secret = auth_setup
        
        # Create expired token
        payload = {
            'user_id': test_user['id'],
            'username': test_user['username'],
            'exp': datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            'iat': datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = jwt.encode(payload, secret, algorithm='HS256')
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                response = test_client.get(
                    '/api/auth/me',
                    headers={'Authorization': f'Bearer {expired_token}'}
                )
                
                assert response.status_code == 401
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
                assert 'expired' in data['error'].lower() or 'invalid' in data['error'].lower()
    
    def test_protected_endpoint_with_malformed_header(self, test_client, auth_setup):
        """Test accessing protected endpoint with malformed Authorization header."""
        auth_service, user_service, test_user, secret = auth_setup
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                # Missing "Bearer " prefix
                response = test_client.get(
                    '/api/auth/me',
                    headers={'Authorization': 'some_token_without_bearer'}
                )
                
                assert response.status_code == 401
                assert response.is_json
                data = response.get_json()
                assert 'error' in data
    
    def test_chat_endpoint_requires_authentication(self, test_client, auth_setup, temp_db):
        """Test that chat endpoint requires authentication and returns JSON errors."""
        auth_service, user_service, test_user, secret = auth_setup
        memory_manager, db_path = temp_db
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                with patch('app.memory_manager', memory_manager):
                    # Try to access chat endpoint without token
                    response = test_client.post(
                        '/api/chat',
                        json={'message': 'Hello'},
                        content_type='application/json'
                    )
                    
                    assert response.status_code == 401
                    # Verify response is JSON (not HTML)
                    assert response.is_json
                    content_type = response.headers.get('Content-Type', '')
                    assert 'application/json' in content_type
                    
                    data = response.get_json()
                    assert 'error' in data
                    assert 'authentication' in data['error'].lower() or 'token' in data['error'].lower()
    
    def test_chat_endpoint_with_valid_token(self, test_client, auth_setup, temp_db, mock_chatbot):
        """Test that chat endpoint works with valid token."""
        auth_service, user_service, test_user, secret = auth_setup
        memory_manager, db_path = temp_db
        
        # Generate token
        token = auth_service.generate_token(test_user['id'], test_user['username'])
        
        with patch('app.auth_service', auth_service):
            with patch('app.user_service', user_service):
                # Patch middleware-level services too (token_required uses these)
                with patch('src.auth.middleware.auth_service', auth_service):
                    with patch('src.auth.middleware.user_service', user_service):
                        with patch('app.memory_manager', memory_manager):
                            with patch('app.get_chatbot', return_value=mock_chatbot):
                                response = test_client.post(
                                    '/api/chat',
                                    json={'message': 'Hello'},
                                    content_type='application/json',
                                    headers={'Authorization': f'Bearer {token}'}
                                )
                                
                                assert response.status_code == 200
                                assert response.is_json
                                data = response.get_json()
                                assert 'response' in data
                                assert 'conversation_id' in data
    
    def test_auth_service_not_configured(self, test_client):
        """Test that endpoints return proper JSON error when auth is not configured."""
        # Mock auth services as None at both app and middleware levels
        with patch('app.auth_service', None):
            with patch('app.user_service', None):
                with patch('src.auth.middleware.auth_service', None):
                    with patch('src.auth.middleware.user_service', None):
                        # Login endpoint should return 503 with JSON
                        response = test_client.post(
                            '/api/auth/login',
                            json={'username': 'test', 'password': 'test'},
                            content_type='application/json'
                        )
                        
                        assert response.status_code == 503
                        assert response.is_json
                        data = response.get_json()
                        assert 'error' in data
                        assert 'not configured' in data['error'].lower()
                        
                        # Protected endpoint should also return JSON (503 when auth not configured)
                        response = test_client.get('/api/auth/me')
                        # Should return 503 (auth not configured) or 401 (no token)
                        # Both are valid - the important thing is it returns JSON
                        assert response.status_code in [401, 503]
                        assert response.is_json
                        data = response.get_json()
                        assert 'error' in data

