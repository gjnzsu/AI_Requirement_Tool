#!/usr/bin/env python3
"""
Script to update user passwords for the chatbot authentication system.

Usage:
    python scripts/update_password.py --username admin --new-password securepass
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
    parser = argparse.ArgumentParser(description='Update a user password')
    parser.add_argument('--username', required=True, help='Username to update')
    parser.add_argument('--new-password', required=True, help='New password')
    parser.add_argument('--db-path', help='Path to auth database (optional, uses default if not specified)')
    
    args = parser.parse_args()
    
    try:
        # Initialize user service
        db_path = args.db_path or Config.AUTH_DB_PATH
        user_service = UserService(db_path=db_path)
        
        # Get user by username to find their ID
        user = user_service.get_user_by_username(args.username)
        if not user:
            print(f"❌ Error: User '{args.username}' not found", file=sys.stderr)
            sys.exit(1)
        
        # Update password
        success = user_service.update_password(user['id'], args.new_password)
        
        if success:
            print("=" * 70)
            print("✅ Password updated successfully!")
            print("=" * 70)
            print(f"   Username: {user['username']}")
            print(f"   Email: {user['email']}")
            print(f"   User ID: {user['id']}")
            print("=" * 70)
        else:
            print(f"❌ Error: Failed to update password for user '{args.username}'", file=sys.stderr)
            sys.exit(1)
        
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

