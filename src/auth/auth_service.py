"""
Authentication service for JWT token generation and validation.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('chatbot.auth')


class AuthService:
    """Service for handling JWT authentication and password operations."""
    
    def __init__(self):
        """Initialize the authentication service."""
        self.secret_key = Config.JWT_SECRET_KEY
        self.expiration_hours = Config.JWT_EXPIRATION_HOURS
        
        # Check if secret key is set and not the default placeholder
        if not self.secret_key or self.secret_key == 'your-secret-key-change-in-production':
            raise ValueError("JWT_SECRET_KEY must be set in configuration. Please set a secure secret key in your .env file.")
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def generate_token(self, user_id: int, username: str) -> str:
        """
        Generate a JWT token for a user.
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            JWT token string
        """
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=self.expiration_hours),
            'iat': datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    def extract_token_from_header(self, auth_header: Optional[str]) -> Optional[str]:
        """
        Extract token from Authorization header.
        
        Args:
            auth_header: Authorization header value (e.g., "Bearer <token>")
            
        Returns:
            Token string if found, None otherwise
        """
        if not auth_header:
            return None
        
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                return None
            return token
        except ValueError:
            return None
