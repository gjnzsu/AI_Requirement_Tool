# Authentication Setup Guide

This guide explains how to set up and use the JWT-based authentication system for the chatbot service.

## Overview

The authentication system provides:
- **JWT-based authentication** - Stateless token-based authentication
- **User management** - Admin-created user accounts (no self-registration)
- **Protected API endpoints** - All chatbot API routes require authentication
- **Login UI** - Beautiful login page matching the chatbot UI design

## Initial Setup

### 1. Install Dependencies

Install the required authentication packages:

```bash
pip install PyJWT>=2.8.0 bcrypt>=4.0.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Configure JWT Secret Key

Set a strong secret key for JWT token signing in your `.env` file:

```env
JWT_SECRET_KEY=your-very-secure-secret-key-change-in-production
JWT_EXPIRATION_HOURS=24
```

**Important:** Use a strong, random secret key in production. You can generate one using:

```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. Create Initial User Account

Use the provided script to create your first admin user:

```bash
python scripts/create_user.py --username admin --email admin@example.com --password your-secure-password
```

You can create additional users using the same script:

```bash
python scripts/create_user.py --username user1 --email user1@example.com --password password123
```

## Usage

### Login Flow

1. **Access the application**: Navigate to `http://localhost:5000`
2. **Redirect to login**: If not authenticated, you'll be redirected to `/login`
3. **Enter credentials**: Use the username and password created via the script
4. **Access granted**: After successful login, you'll be redirected to the main chat interface

### API Authentication

All API endpoints (except `/api/auth/login`) require authentication:

- **Token Storage**: JWT tokens are stored in browser `localStorage`
- **Automatic Inclusion**: Tokens are automatically included in API requests via `Authorization: Bearer <token>` header
- **Token Expiration**: Tokens expire after 24 hours (configurable via `JWT_EXPIRATION_HOURS`)
- **Auto-redirect**: Expired tokens automatically redirect users to the login page

### Protected Endpoints

The following endpoints require authentication:
- `POST /api/chat` - Send chat messages
- `GET /api/conversations` - List conversations
- `GET /api/conversations/<id>` - Get specific conversation
- `DELETE /api/conversations/<id>` - Delete conversation
- `DELETE /api/conversations` - Clear all conversations
- `PUT /api/conversations/<id>/title` - Update conversation title
- `POST /api/new-chat` - Create new chat
- `GET /api/current-model` - Get current model
- `GET /api/search` - Search conversations

### Public Endpoints

- `GET /` - Main chat interface (redirects to login if not authenticated)
- `GET /login` - Login page
- `POST /api/auth/login` - Login endpoint
- `POST /api/auth/logout` - Logout endpoint (requires authentication)
- `GET /api/auth/me` - Get current user info (requires authentication)

## User Management

### Creating Users

Only administrators can create user accounts using the command-line script:

```bash
python scripts/create_user.py --username <username> --email <email> --password <password>
```

### User Database

User accounts are stored in SQLite database at `data/auth.db` by default. You can customize the path via:

```env
AUTH_DB_PATH=/path/to/auth.db
```

### User Schema

Users table structure:
- `id` - Unique user ID
- `username` - Unique username
- `email` - Unique email address
- `password_hash` - Bcrypt-hashed password
- `created_at` - Account creation timestamp
- `is_active` - Account status (1 = active, 0 = inactive)

## Security Considerations

1. **Password Security**
   - Passwords are hashed using bcrypt with cost factor 12
   - Never store plaintext passwords

2. **JWT Security**
   - Use strong secret keys in production
   - Tokens expire after configured hours
   - Tokens are stored client-side (localStorage)

3. **HTTPS**
   - **Important**: Use HTTPS in production to protect tokens in transit
   - Never transmit tokens over unencrypted connections

4. **Token Storage**
   - Tokens are stored in browser localStorage
   - Consider implementing refresh tokens for enhanced security in production

## Troubleshooting

### "Authentication required" Error

- Check if you're logged in (token exists in localStorage)
- Verify token hasn't expired
- Try logging out and logging back in

### "Invalid username or password" Error

- Verify username and password are correct
- Check if user account exists: `python scripts/create_user.py --username <username> ...`
- Ensure user account is active

### Token Expiration

- Tokens expire after 24 hours by default
- Users are automatically redirected to login when token expires
- Adjust expiration time via `JWT_EXPIRATION_HOURS` in `.env`

### Database Issues

- Ensure `data/` directory exists and is writable
- Check database path configuration
- Verify SQLite is available

## Configuration Reference

Add these to your `.env` file:

```env
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_EXPIRATION_HOURS=24

# Optional: Custom auth database path
AUTH_DB_PATH=data/auth.db
```

## Example: Complete Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set JWT secret key in .env
echo "JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
echo "JWT_EXPIRATION_HOURS=24" >> .env

# 3. Create admin user
python scripts/create_user.py --username admin --email admin@example.com --password Admin123!

# 4. Start the application
python app.py

# 5. Access http://localhost:5000 and login with admin credentials
```

## Next Steps

- Consider implementing password reset functionality
- Add user profile management
- Implement role-based access control (RBAC) if needed
- Add session management and refresh tokens for enhanced security
