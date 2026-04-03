"""Authentication routes for the Flask web app."""

from flask import Blueprint, jsonify, request

from src.webapp import get_app_runtime

try:
    from src.auth import get_current_user, token_required
except ImportError:
    token_required = lambda f: f
    get_current_user = lambda: None


auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate a user and return a JWT token."""
    runtime = get_app_runtime()
    auth_service = runtime.auth_service
    user_service = runtime.user_service

    if not auth_service or not user_service:
        return jsonify({'error': 'Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.'}), 503

    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        user = user_service.authenticate_user(username, password)
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401

        token = auth_service.generate_token(user['id'], user['username'])
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        })
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@auth_blueprint.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    """Logout the current user."""
    runtime = get_app_runtime()
    if not runtime.auth_service or not runtime.user_service:
        return jsonify({'error': 'Authentication is not configured.'}), 503

    return jsonify({'success': True, 'message': 'Logged out successfully'})


@auth_blueprint.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user_info():
    """Return details for the currently authenticated user."""
    user = get_current_user()
    if user:
        return jsonify({'user': user})
    return jsonify({'error': 'User not found'}), 404