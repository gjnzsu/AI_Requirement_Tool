"""
Authentication module for chatbot service.

Provides JWT-based authentication, user management, and route protection.
"""

from .auth_service import AuthService
from .user_service import UserService
from .middleware import token_required, get_current_user

__all__ = ['AuthService', 'UserService', 'token_required', 'get_current_user']
