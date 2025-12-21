"""
User management service for authentication.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from contextlib import contextmanager
from config.config import Config
from src.auth.auth_service import AuthService
from src.utils.logger import get_logger

logger = get_logger('chatbot.auth.user')


class UserService:
    """Service for managing user accounts."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the user service.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'auth.db')
        
        self.db_path = db_path
        
        # Initialize AuthService with error handling
        try:
            self.auth_service = AuthService()
        except (ValueError, Exception) as e:
            logger.warning(f"AuthService not initialized: {e}. Password operations will be unavailable.")
            self.auth_service = None
        
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database with users table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON users(email)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def create_user(self, username: str, email: str, password: str) -> Dict:
        """
        Create a new user account.
        
        Args:
            username: Username (must be unique)
            email: Email address (must be unique)
            password: Plain text password
            
        Returns:
            Dictionary with user information (without password hash)
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if user already exists
        if self.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")
        
        if self.get_user_by_email(email):
            raise ValueError(f"Email '{email}' already exists")
        
        # Hash password
        if not self.auth_service:
            raise ValueError("Authentication service is not configured. Please set JWT_SECRET_KEY in your .env file.")
        password_hash = self.auth_service.hash_password(password)
        
        # Create user
        created_at = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, created_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (username, email, password_hash, created_at, 1))
            conn.commit()
            user_id = cursor.lastrowid
        
        logger.info(f"Created user: {username} (ID: {user_id})")
        
        return {
            'id': user_id,
            'username': username,
            'email': email,
            'created_at': created_at,
            'is_active': True
        }
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username.
        
        Args:
            username: Username to lookup
            
        Returns:
            User dictionary if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, password_hash, created_at, is_active
                FROM users
                WHERE username = ? AND is_active = 1
            """, (username,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'username': row['username'],
                    'email': row['email'],
                    'password_hash': row['password_hash'],
                    'created_at': row['created_at'],
                    'is_active': bool(row['is_active'])
                }
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email.
        
        Args:
            email: Email to lookup
            
        Returns:
            User dictionary if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, password_hash, created_at, is_active
                FROM users
                WHERE email = ? AND is_active = 1
            """, (email,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'username': row['username'],
                    'email': row['email'],
                    'password_hash': row['password_hash'],
                    'created_at': row['created_at'],
                    'is_active': bool(row['is_active'])
                }
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID to lookup
            
        Returns:
            User dictionary if found, None otherwise (without password hash)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, created_at, is_active
                FROM users
                WHERE id = ? AND is_active = 1
            """, (user_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row['id'],
                    'username': row['username'],
                    'email': row['email'],
                    'created_at': row['created_at'],
                    'is_active': bool(row['is_active'])
                }
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            User dictionary if authentication succeeds, None otherwise
        """
        user = self.get_user_by_username(username)
        
        if not user:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return None
        
        if not self.auth_service:
            logger.error("Authentication service is not configured")
            return None
        
        if not self.auth_service.verify_password(password, user['password_hash']):
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
            return None
        
        # Return user without password hash
        return {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'created_at': user['created_at'],
            'is_active': user['is_active']
        }
    
    def list_users(self) -> List[Dict]:
        """
        List all active users.
        
        Returns:
            List of user dictionaries (without password hashes)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, created_at, is_active
                FROM users
                WHERE is_active = 1
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row['id'],
                    'username': row['username'],
                    'email': row['email'],
                    'created_at': row['created_at'],
                    'is_active': bool(row['is_active'])
                }
                for row in rows
            ]
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """
        Update user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password
            
        Returns:
            True if successful, False otherwise
        """
        if not self.auth_service:
            logger.error("Authentication service is not configured")
            return False
        
        password_hash = self.auth_service.hash_password(new_password)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET password_hash = ?
                WHERE id = ? AND is_active = 1
            """, (password_hash, user_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Updated password for user ID: {user_id}")
                return True
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        Deactivate a user account.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET is_active = 0
                WHERE id = ?
            """, (user_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Deactivated user ID: {user_id}")
                return True
            return False
