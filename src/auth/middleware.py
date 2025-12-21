"""
Authentication middleware for Flask routes.
"""

from functools import wraps
from flask import request, jsonify
from typing import Optional, Dict
from src.auth.auth_service import AuthService
from src.auth.user_service import UserService
from src.utils.logger import get_logger

logger = get_logger('chatbot.auth.middleware')

# Initialize services (with error handling)
try:
    auth_service = AuthService()
    user_service = UserService()
except (ValueError, Exception) as e:
    logger.warning(f"Authentication services not initialized: {e}")
    auth_service = None
    user_service = None


def token_required(f):
    """
    Decorator to protect Flask routes with JWT authentication.
    
    Usage:
        @app.route('/api/protected')
        @token_required
        def protected_route():
            # Access current user via request.current_user
            return jsonify({'user': request.current_user})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if authentication services are available
        if not auth_service or not user_service:
            return jsonify({
                'error': 'Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.'
            }), 503
        
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        token = auth_service.extract_token_from_header(auth_header)
        
        if not token:
            return jsonify({'error': 'Authentication required. Please provide a valid token.'}), 401
        
        # Verify token
        payload = auth_service.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token. Please login again.'}), 401
        
        # Get user from database
        user_id = payload.get('user_id')
        user = user_service.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found or inactive.'}), 401
        
        # Attach user to request object
        request.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated


def get_current_user() -> Optional[Dict]:
    """
    Get the current authenticated user from the request.
    
    Returns:
        User dictionary if authenticated, None otherwise
        
    Note: This should be called within a route decorated with @token_required
    """
    return getattr(request, 'current_user', None)
