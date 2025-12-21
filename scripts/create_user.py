#!/usr/bin/env python3
"""
Script to create user accounts for the chatbot authentication system.

Usage:
    python scripts/create_user.py --username admin --email admin@example.com --password securepass
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.auth import UserService
from config.config import Config


def main():
    parser = argparse.ArgumentParser(description='Create a new user account')
    parser.add_argument('--username', required=True, help='Username (must be unique)')
    parser.add_argument('--email', required=True, help='Email address (must be unique)')
    parser.add_argument('--password', required=True, help='Password')
    parser.add_argument('--db-path', help='Path to auth database (optional, uses default if not specified)')
    
    args = parser.parse_args()
    
    try:
        # Initialize user service
        db_path = args.db_path or Config.AUTH_DB_PATH
        user_service = UserService(db_path=db_path)
        
        # Create user
        user = user_service.create_user(
            username=args.username,
            email=args.email,
            password=args.password
        )
        
        print("=" * 70)
        print("✅ User created successfully!")
        print("=" * 70)
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   User ID: {user['id']}")
        print(f"   Created at: {user['created_at']}")
        print("=" * 70)
        
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
