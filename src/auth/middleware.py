"""
Authentication middleware for Flask routes.
"""

import sys
from functools import wraps
from flask import current_app, has_app_context, request, jsonify
from typing import Optional, Dict
from werkzeug.local import LocalProxy
from src.auth.auth_service import AuthService
from src.auth.user_service import UserService
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('chatbot.auth.middleware')

# Initialize services (with error handling)
try:
    auth_service = AuthService()
    user_service = UserService(db_path=Config.AUTH_DB_PATH)
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
        try:
            active_auth_service, active_user_service = _resolve_auth_dependencies()

            # Optional: allow explicitly bypassing auth (useful for non-auth API tests)
            # NOTE: We do NOT automatically bypass just because pytest is running, since
            # `tests/integration/api/test_auth_api.py` expects real auth behavior.
            import os
            if os.environ.get('BYPASS_AUTH', '').strip() in ('1', 'true', 'True', 'yes', 'YES'):
                request.current_user = {'id': 1, 'username': 'test_user', 'email': 'test@example.com'}
                return f(*args, **kwargs)
            
            # Check if authentication services are available
            if not active_auth_service or not active_user_service:
                return jsonify({
                    'error': 'Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.'
                }), 503
            
            token = None
            
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            # Removed INFO log - only log at DEBUG level for troubleshooting
            
            if active_auth_service:
                token = active_auth_service.extract_token_from_header(auth_header)
                if token:
                    # Changed to DEBUG - only log if needed for troubleshooting
                    logger.debug(f"[AUTH] Token extracted successfully (first 20 chars: {token[:20]}...)")
                else:
                    log_msg = f"[AUTH] No token extracted from header: {auth_header}"
                    logger.warning(log_msg)
                    # Removed INFO log - changed to DEBUG for troubleshooting
                    logger.debug(f"[AUTH] All request headers: {dict(request.headers)}")
            else:
                return jsonify({
                    'error': 'Authentication service is not available.'
                }), 503
            
            if not token:
                log_msg = f"[AUTH] 401 Unauthorized for {request.path}: No token provided. Headers: {list(request.headers.keys())}"
                logger.warning(log_msg)
                return jsonify({'error': 'Authentication required. Please provide a valid token.'}), 401
            
            # Verify token
            payload = active_auth_service.verify_token(token)
            if not payload:
                log_msg = f"[AUTH] Token verification failed for {request.path}"
                logger.warning(log_msg)
                return jsonify({'error': 'Invalid or expired token. Please login again.'}), 401
            
            # Changed to DEBUG - removed INFO log
            logger.debug(f"[AUTH] Token verified successfully. Payload: user_id={payload.get('user_id')}, username={payload.get('username')}")
            
            # Get user from database
            user_id = payload.get('user_id')
            if active_user_service:
                # Changed to DEBUG - removed INFO log
                db_path = getattr(active_user_service, 'db_path', 'unknown')
                logger.debug(f"[AUTH] Looking up user_id={user_id} in database: {db_path}")
                
                user = active_user_service.get_user_by_id(user_id)
                if user:
                    # Changed to DEBUG - removed INFO log
                    logger.debug(f"[AUTH] User found: id={user.get('id')}, username={user.get('username')}")
                else:
                    log_msg = f"[AUTH] User not found for user_id={user_id} in database: {db_path}"
                    logger.warning(log_msg)
            else:
                return jsonify({
                    'error': 'User service is not available.'
                }), 503
            
            if not user:
                log_msg = f"[AUTH] 401 Unauthorized: User not found or inactive for user_id={user_id}"
                logger.warning(log_msg)
                return jsonify({'error': 'User not found or inactive.'}), 401
            
            # Attach user to request object
            request.current_user = user
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}", exc_info=True)
            return jsonify({
                'error': 'Authentication error',
                'message': str(e)
            }), 500
    
    return decorated


def _resolve_auth_dependencies():
    """Return the active auth/user services, honoring runtime state and test patches."""
    app_module = sys.modules.get('app')
    if app_module is not None:
        module_auth_service = app_module.__dict__.get('auth_service')
        module_user_service = app_module.__dict__.get('user_service')
        if not isinstance(module_auth_service, LocalProxy) or not isinstance(module_user_service, LocalProxy):
            return module_auth_service, module_user_service

    if has_app_context():
        runtime = current_app.extensions.get('chatbot_runtime')
        if runtime is not None:
            return runtime.auth_service, runtime.user_service

    return auth_service, user_service


def get_current_user() -> Optional[Dict]:
    """
    Get the current authenticated user from the request.
    
    Returns:
        User dictionary if authenticated, None otherwise
        
    Note: This should be called within a route decorated with @token_required
    """
    return getattr(request, 'current_user', None)
