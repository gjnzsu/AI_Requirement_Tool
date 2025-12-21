# Swagger API Documentation Usage Guide

## Overview

The chatbot API now includes interactive Swagger documentation powered by Flasgger. This allows you to explore, test, and understand all API endpoints directly from your browser.

## Accessing Swagger UI

1. **Start the application:**
   ```bash
   python app.py
   ```

2. **Open Swagger UI:**
   Navigate to: `http://localhost:5000/api/docs`

3. **View API Specification (JSON):**
   Navigate to: `http://localhost:5000/apispec.json`

## Features

### Interactive API Testing

- **Try It Out**: Click "Try it out" on any endpoint to test it
- **Fill Parameters**: Enter request parameters directly in the UI
- **Execute Requests**: Send requests and see responses in real-time
- **View Examples**: See example request/response payloads

### Authentication

1. **Login First:**
   - Use the `/api/auth/login` endpoint
   - Enter your username and password
   - Copy the returned `token`

2. **Authorize:**
   - Click the "Authorize" button at the top of Swagger UI
   - Enter: `Bearer <your-token>` (replace `<your-token>` with actual token)
   - Click "Authorize"
   - Now all protected endpoints will include your token automatically

### Endpoint Categories

The API is organized into the following tags:

- **Authentication**: Login, logout, get current user
- **Chat**: Send messages to the chatbot
- **Conversations**: Manage conversations (list, get, delete, update title, create new)
- **Models**: Get current model information

## Example Workflow

### 1. Login and Get Token

```
POST /api/auth/login
Body:
{
  "username": "admin",
  "password": "your-password"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

### 2. Authorize in Swagger UI

- Click "Authorize" button
- Enter: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- Click "Authorize"

### 3. Test Chat Endpoint

```
POST /api/chat
Body:
{
  "message": "What is Python?",
  "model": "openai"
}

Response:
{
  "response": "Python is a high-level programming language...",
  "conversation_id": "conv_20240101_120000",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 4. List Conversations

```
GET /api/conversations

Response:
{
  "conversations": [
    {
      "id": "conv_20240101_120000",
      "title": "Python Questions",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T13:30:00",
      "message_count": 5
    }
  ]
}
```

## API Endpoints Summary

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/login` | Login and get JWT token | No |
| POST | `/api/auth/logout` | Logout current user | Yes |
| GET | `/api/auth/me` | Get current user info | Yes |

### Chat Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/chat` | Send message to chatbot | Yes |

### Conversation Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/conversations` | List all conversations | Yes |
| GET | `/api/conversations/<id>` | Get specific conversation | Yes |
| DELETE | `/api/conversations/<id>` | Delete conversation | Yes |
| DELETE | `/api/conversations` | Clear all conversations | Yes |
| PUT | `/api/conversations/<id>/title` | Update conversation title | Yes |
| POST | `/api/new-chat` | Create new conversation | Yes |
| GET | `/api/search` | Search conversations | Yes |

### Model Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/current-model` | Get current LLM model | Yes |

## Response Codes

- **200**: Success
- **400**: Bad Request (missing/invalid parameters)
- **401**: Unauthorized (invalid/missing token)
- **404**: Not Found (resource doesn't exist)
- **429**: Rate Limit Exceeded
- **500**: Internal Server Error

## Tips

1. **Token Expiration**: JWT tokens expire after 24 hours (configurable). If you get 401 errors, login again to get a new token.

2. **Model Selection**: You can specify the LLM provider per request using the `model` parameter in the chat endpoint. Supported values: `openai`, `gemini`, `deepseek`.

3. **Conversation Context**: Include `conversation_id` in chat requests to maintain conversation context across multiple messages.

4. **Error Handling**: All error responses include an `error` field with a descriptive message.

5. **Search**: The search endpoint searches both conversation titles and message content.

## Troubleshooting

### Swagger UI Not Loading

- Ensure `flasgger` is installed: `pip install flasgger`
- Check that the server is running on port 5000
- Verify the route `/api/docs` is accessible

### 401 Unauthorized Errors

- Make sure you've logged in and copied the token
- Click "Authorize" and enter: `Bearer <your-token>`
- Check if token has expired (login again)

### Endpoints Not Showing

- Refresh the Swagger UI page
- Check browser console for errors
- Verify all endpoints have Swagger docstrings

## Benefits

- **Self-Documenting**: API documentation stays in sync with code
- **Interactive Testing**: Test endpoints without writing code
- **Client Generation**: Can generate API clients from the spec
- **Team Collaboration**: Share API documentation easily
- **Onboarding**: New developers can understand the API quickly

## Next Steps

- Explore all endpoints in Swagger UI
- Test different request combinations
- Use the examples as reference for integration
- Generate API clients if needed (using OpenAPI generators)
