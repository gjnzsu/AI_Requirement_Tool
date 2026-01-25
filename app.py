"""
Flask Web Application for Chatbot UI.

This provides a REST API and serves the web interface for the chatbot.
"""

import sys
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect
from flask_cors import CORS
import json
from datetime import datetime
from typing import Dict, List
import concurrent.futures
import threading

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Helper function for safe printing on Windows (handles Unicode encoding issues)
def safe_print(message):
    """Print message safely, handling Unicode encoding issues on Windows."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: replace Unicode characters with ASCII equivalents
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

# Import with error handling to prevent startup failures
try:
    from src.chatbot import Chatbot
except ImportError as e:
    safe_print(f"[WARNING] Could not import Chatbot: {e}")
    Chatbot = None

try:
    from src.services.memory_manager import MemoryManager
except ImportError as e:
    safe_print(f"[WARNING] Could not import MemoryManager: {e}")
    MemoryManager = None

try:
    from src.auth import AuthService, UserService, token_required, get_current_user
except ImportError as e:
    safe_print(f"[WARNING] Could not import auth modules: {e}")
    safe_print("  Authentication features will be disabled.")
    AuthService = None
    UserService = None
    token_required = lambda f: f  # No-op decorator
    get_current_user = lambda: None

from config.config import Config

# Try to import logger
try:
    from src.utils.logger import get_logger
except ImportError:
    # Fallback logger if logger module not available
    def get_logger(name):
        import logging
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

# Try to import flasgger for Swagger documentation
try:
    from flasgger import Swagger
    SWAGGER_AVAILABLE = True
except ImportError:
    SWAGGER_AVAILABLE = False
    safe_print("[WARNING] Flasgger not installed. Swagger documentation will not be available.")
    safe_print("   Install with: pip install flasgger")

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)

# Initialize Swagger if available
if SWAGGER_AVAILABLE:
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "Chatbot API",
            "description": "REST API for Generative AI Chatbot with authentication, conversation management, and multi-provider LLM support (OpenAI, Gemini, DeepSeek).",
            "version": "1.0.0",
            "contact": {
                "name": "API Support"
            }
        },
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
            }
        },
        "security": [
            {
                "Bearer": []
            }
        ]
    }
    
    swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Global chatbot instance
chatbot_instance = None
memory_manager = None
conversations = {}  # Fallback in-memory storage when persistent memory is disabled

# Initialize authentication services
auth_service = None
user_service = None

if AuthService is not None and UserService is not None:
    try:
        auth_service = AuthService()
        db_path = Config.AUTH_DB_PATH
        safe_print(f"[OK] Initialized Authentication services")
        safe_print(f"     Config.AUTH_DB_PATH: {db_path}")
        safe_print(f"     Environment AUTH_DB_PATH: {os.getenv('AUTH_DB_PATH', 'Not set')}")
        user_service = UserService(db_path=db_path)
        # Log the actual database path being used
        actual_db_path = user_service.db_path
        safe_print(f"     Using database at: {actual_db_path}")
        # Verify database exists and has users
        try:
            users = user_service.list_users()
            safe_print(f"     Users in database: {len(users)}")
            for user in users:
                safe_print(f"       - ID: {user['id']}, Username: {user['username']}")
        except Exception as e:
            safe_print(f"     Warning: Could not list users: {e}")
    except ValueError as e:
        safe_print(f"[WARNING] Authentication initialization warning: {e}")
        safe_print("   Authentication will be disabled. Set JWT_SECRET_KEY in .env to enable.")
        auth_service = None
        user_service = None
    except Exception as e:
        safe_print(f"[WARNING] Failed to initialize Authentication services: {e}")
        safe_print("   Authentication will be disabled.")
        auth_service = None
        user_service = None
else:
    safe_print("[WARNING] Authentication modules not available. Authentication will be disabled.")

# Initialize memory manager if enabled
if MemoryManager is not None and Config.USE_PERSISTENT_MEMORY:
    try:
        memory_manager = MemoryManager(
            db_path=Config.MEMORY_DB_PATH,
            max_context_messages=Config.MAX_CONTEXT_MESSAGES
        )
        safe_print("[OK] Initialized Memory Manager for web app")
    except Exception as e:
        safe_print(f"[WARNING] Failed to initialize Memory Manager: {e}")
        memory_manager = None
        safe_print("   Falling back to in-memory storage")
else:
    memory_manager = None
    if MemoryManager is None:
        safe_print("[WARNING] MemoryManager not available. Using in-memory storage.")
    else:
        safe_print("[WARNING] Persistent memory disabled (USE_PERSISTENT_MEMORY=false)")

def get_chatbot():
    """Get or create chatbot instance with timeout protection."""
    global chatbot_instance
    
    if Chatbot is None:
        raise RuntimeError("Chatbot module is not available. Please install required dependencies.")
    
    if chatbot_instance is None:
        print("=" * 70)
        print("🤖 Creating Chatbot Instance")
        print("=" * 70)
        print(f"   Provider: {Config.LLM_PROVIDER}")
        print(f"   Model: {Config.get_llm_model()}")
        print(f"   MCP Enabled: {Config.USE_MCP}")
        print(f"   RAG Enabled: {getattr(Config, 'USE_RAG', True)}")
        print(f"   Tools Enabled: {getattr(Config, 'ENABLE_MCP_TOOLS', True)}")
        print("=" * 70)
        
        # Use timeout wrapper to prevent hanging during initialization (especially in tests)
        # 120 seconds should be enough for normal initialization
        def _create_chatbot():
            return Chatbot(
                provider_name=None,  # Use default from Config
                use_fallback=True,
                temperature=0.7,
                max_history=Config.MAX_CONTEXT_MESSAGES // 2,  # Convert to turns
                use_persistent_memory=Config.USE_PERSISTENT_MEMORY,
                memory_db_path=Config.MEMORY_DB_PATH,
                use_rag=getattr(Config, 'USE_RAG', True),
                rag_top_k=getattr(Config, 'RAG_TOP_K', 3),
                enable_mcp_tools=getattr(Config, 'ENABLE_MCP_TOOLS', True),
                lazy_load_tools=True,  # Lazy load tools to avoid dead loops
                use_agent=True,  # Enable LangGraph agent for intelligent routing
                use_mcp=Config.USE_MCP  # Use MCP protocol if enabled in config
            )
        
        try:
            # Check if we're in a test environment (pytest sets this)
            import os
            if os.environ.get('PYTEST_CURRENT_TEST') or os.environ.get('TESTING'):
                # In tests, don't use timeout wrapper - let tests handle mocking
                chatbot_instance = _create_chatbot()
            else:
                # In production, use timeout wrapper to prevent hangs
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(_create_chatbot)
                    try:
                        chatbot_instance = future.result(timeout=120.0)  # 120 second timeout
                    except concurrent.futures.TimeoutError:
                        raise RuntimeError(
                            "Chatbot initialization timed out after 120 seconds. "
                            "This may indicate a configuration issue or network problem."
                        )
        except Exception as e:
            print(f"❌ Chatbot initialization failed: {e}")
            raise
        
        print("=" * 70)
        print("✅ Chatbot Instance Created Successfully")
        print("=" * 70)
    return chatbot_instance

def generate_conversation_id():
    """Generate a unique conversation ID."""
    return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

@app.route('/')
def index():
    """Serve the main chat interface."""
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Serve the login page."""
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    # Check if authentication is enabled
    if not auth_service or not user_service:
        return jsonify({'error': 'Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.'}), 503
    """
    User Login
    ---
    tags:
      - Authentication
    summary: Authenticate user and receive JWT token
    description: Login with username and password to receive a JWT authentication token. This token must be included in the Authorization header for protected endpoints.
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: credentials
        description: User login credentials
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: Username
              example: admin
            password:
              type: string
              format: password
              description: User password
              example: password123
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            token:
              type: string
              description: JWT authentication token (valid for 24 hours by default)
              example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZXhwIjoxNzA0MTAwMDAwfQ.example
            user:
              type: object
              description: User information
              properties:
                id:
                  type: integer
                  description: User ID
                  example: 1
                username:
                  type: string
                  description: Username
                  example: admin
                email:
                  type: string
                  description: Email address
                  example: admin@example.com
      400:
        description: Missing username or password
        schema:
          type: object
          properties:
            error:
              type: string
              example: Username and password are required
      401:
        description: Invalid credentials
        schema:
          type: object
          properties:
            error:
              type: string
              example: Invalid username or password
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Check if authentication services are available
        if not auth_service or not user_service:
            return jsonify({
                'error': 'Authentication is not configured. Please set JWT_SECRET_KEY in your .env file.'
            }), 503
        
        # Authenticate user
        user = user_service.authenticate_user(username, password)
        
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Generate JWT token
        token = auth_service.generate_token(user['id'], user['username'])
        
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout():
    # Check if authentication is enabled
    if not auth_service or not user_service:
        return jsonify({'error': 'Authentication is not configured.'}), 503
    """
    User Logout
    ---
    tags:
      - Authentication
    summary: Logout current user
    description: Logout endpoint. Note that token removal is handled client-side (localStorage). This endpoint confirms logout on the server side.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Logout successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Logged out successfully
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
    """
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user_info():
    """
    Get Current User
    ---
    tags:
      - Authentication
    summary: Get current authenticated user information
    description: Returns information about the currently authenticated user based on the JWT token.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: User information retrieved successfully
        schema:
          type: object
          properties:
            user:
              type: object
              description: User details
              properties:
                id:
                  type: integer
                  description: User ID
                  example: 1
                username:
                  type: string
                  description: Username
                  example: admin
                email:
                  type: string
                  description: Email address
                  example: admin@example.com
                created_at:
                  type: string
                  format: date-time
                  description: Account creation timestamp
                  example: "2024-01-01T00:00:00"
                is_active:
                  type: boolean
                  description: Account active status
                  example: true
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Invalid or expired token. Please login again.
      404:
        description: User not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: User not found
    """
    user = get_current_user()
    if user:
        return jsonify({'user': user})
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/chat', methods=['POST'])
@token_required
def chat():
    """
    Send Chat Message
    ---
    tags:
      - Chat
    summary: Send a message to the chatbot
    description: Send a message to the chatbot and receive an AI-generated response. Supports multiple LLM providers (OpenAI, Gemini, DeepSeek). The conversation context is maintained if a conversation_id is provided.
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: message
        description: Chat message and conversation context
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              description: User message to send to the chatbot
              example: "What is Python?"
            conversation_id:
              type: string
              description: Optional conversation ID to continue an existing conversation. If not provided, a new conversation will be created.
              example: "conv_20240101_120000"
            model:
              type: string
              description: LLM provider to use for this request
              enum: [openai, gemini, deepseek]
              default: openai
              example: openai
    responses:
      200:
        description: Chat response received successfully
        schema:
          type: object
          properties:
            response:
              type: string
              description: AI-generated response from the chatbot
              example: "Python is a high-level, interpreted programming language known for its simplicity and readability..."
            conversation_id:
              type: string
              description: Conversation ID (created if not provided in request)
              example: "conv_20240101_120000"
            timestamp:
              type: string
              format: date-time
              description: Response timestamp
              example: "2024-01-01T12:00:00"
      400:
        description: Invalid request (missing message or invalid model)
        schema:
          type: object
          properties:
            error:
              type: string
              example: Message is required
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      429:
        description: Rate limit exceeded
        schema:
          type: object
          properties:
            error:
              type: string
              example: Rate limit exceeded. The API has received too many requests. Please wait a few minutes and try again, or switch to a different model.
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        # Safely parse JSON request body
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        try:
            data = request.get_json(silent=True)
            if data is None:
                return jsonify({'error': 'Invalid JSON in request body'}), 400
        except Exception as e:
            return jsonify({'error': f'Failed to parse JSON: {str(e)}'}), 400
        
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        model = data.get('model', 'openai').lower()  # Get model from request, default to openai
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Validate model
        if model not in ['openai', 'gemini', 'deepseek']:
            return jsonify({'error': f'Invalid model: {model}. Supported models: openai, gemini, deepseek'}), 400
        
        # Get or create conversation
        if not conversation_id or (memory_manager and not memory_manager.get_conversation(conversation_id)):
            conversation_id = generate_conversation_id()
            title = message[:50] + ('...' if len(message) > 50 else '')
            
            if memory_manager:
                memory_manager.create_conversation(conversation_id, title=title)
        
        # Get chatbot response
        chatbot = get_chatbot()
        
        # Switch provider if different from current (case-insensitive comparison)
        if chatbot.provider_name.lower() != model.lower():
            try:
                chatbot.switch_provider(model)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'Failed to switch model: {str(e)}'}), 500
        
        # Set conversation ID for persistent memory
        chatbot.set_conversation_id(conversation_id)
        
        # Load conversation history if using persistent memory
        if memory_manager:
            chatbot.load_conversation(conversation_id)
        
        # Get response (this will automatically save to persistent memory)
        response = chatbot.get_response(message)
        
        # Get updated conversation from memory manager
        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if conversation:
                # Update title if it's the first message
                if len(conversation.get('messages', [])) == 2:
                    memory_manager.update_conversation_title(
                        conversation_id,
                        message[:50] + ('...' if len(message) > 50 else '')
                    )
        
        return jsonify({
            'response': response,
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        # Enhanced error handling with user-friendly messages
        error_type = type(e).__name__
        error_str = str(e).lower()
        
        # Check for HTTP status codes
        http_status_code = None
        if hasattr(e, 'status_code'):
            http_status_code = e.status_code
        elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            http_status_code = e.response.status_code
        elif '429' in error_str:
            http_status_code = 429
        
        # Detect error categories
        is_rate_limit = (
            http_status_code == 429 or
            'RateLimit' in error_type or
            'rate limit' in error_str or
            'quota' in error_str or
            '429' in error_str
        )
        
        if is_rate_limit:
            error_message = (
                "Rate limit exceeded. The API has received too many requests. "
                "Please wait a few minutes and try again, or switch to a different model."
            )
            status_code = 429
        else:
            error_message = str(e)
            status_code = 500
        
        return jsonify({'error': error_message}), status_code

@app.route('/api/conversations', methods=['GET'])
@token_required
def get_conversations():
    """
    List All Conversations
    ---
    tags:
      - Conversations
    summary: Get list of all conversations
    description: Retrieve all conversations for the authenticated user, ordered by most recent update. Returns conversation metadata including title, creation date, and message count.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: List of conversations retrieved successfully
        schema:
          type: object
          properties:
            conversations:
              type: array
              description: List of conversations
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Unique conversation ID
                    example: "conv_20240101_120000"
                  title:
                    type: string
                    description: Conversation title
                    example: "Python Questions"
                  created_at:
                    type: string
                    format: date-time
                    description: Conversation creation timestamp
                    example: "2024-01-01T12:00:00"
                  updated_at:
                    type: string
                    format: date-time
                    description: Last update timestamp
                    example: "2024-01-01T13:30:00"
                  message_count:
                    type: integer
                    description: Number of messages in the conversation
                    example: 5
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        if memory_manager:
            # Get conversations from persistent storage
            conv_list = memory_manager.list_conversations(order_by='updated_at')
            conv_list = [
                {
                    'id': conv['id'],
                    'title': conv['title'],
                    'created_at': conv['created_at'],
                    'updated_at': conv['updated_at'],
                    'message_count': conv.get('message_count', 0)
                }
                for conv in conv_list
            ]
        else:
            # Fallback to in-memory storage (for backward compatibility)
            conv_list = [
                {
                    'id': conv_id,
                    'title': conv['title'],
                    'created_at': conv['created_at'],
                    'updated_at': conv.get('updated_at', conv['created_at']),
                    'message_count': len(conv['messages'])
                }
                for conv_id, conv in conversations.items()
            ]
            conv_list.sort(key=lambda x: x.get('updated_at', x['created_at']), reverse=True)
        
        return jsonify({'conversations': conv_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
@token_required
def get_conversation(conversation_id):
    """
    Get Conversation
    ---
    tags:
      - Conversations
    summary: Get a specific conversation by ID
    description: Retrieve a conversation with all its messages. Returns the full conversation history including user messages and AI responses.
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: path
        name: conversation_id
        type: string
        required: true
        description: Unique conversation ID
        example: "conv_20240101_120000"
    responses:
      200:
        description: Conversation retrieved successfully
        schema:
          type: object
          properties:
            conversation:
              type: object
              description: Full conversation details
              properties:
                id:
                  type: string
                  example: "conv_20240101_120000"
                title:
                  type: string
                  example: "Python Questions"
                messages:
                  type: array
                  description: List of messages in the conversation
                  items:
                    type: object
                    properties:
                      role:
                        type: string
                        enum: [user, assistant]
                        description: Message sender role
                        example: "user"
                      content:
                        type: string
                        description: Message content
                        example: "What is Python?"
                      timestamp:
                        type: string
                        format: date-time
                        example: "2024-01-01T12:00:00"
                created_at:
                  type: string
                  format: date-time
                  example: "2024-01-01T12:00:00"
                updated_at:
                  type: string
                  format: date-time
                  example: "2024-01-01T13:30:00"
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      404:
        description: Conversation not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: Conversation not found
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            
            return jsonify({'conversation': conversation})
        else:
            # Fallback to in-memory storage
            if conversation_id not in conversations:
                return jsonify({'error': 'Conversation not found'}), 404
            
            return jsonify({
                'conversation': conversations[conversation_id]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@token_required
def delete_conversation(conversation_id):
    """
    Delete Conversation
    ---
    tags:
      - Conversations
    summary: Delete a conversation
    description: Permanently delete a conversation by ID. This action cannot be undone.
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: path
        name: conversation_id
        type: string
        required: true
        description: Unique conversation ID to delete
        example: "conv_20240101_120000"
    responses:
      200:
        description: Conversation deleted successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      404:
        description: Conversation not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: Conversation not found
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            
            memory_manager.delete_conversation(conversation_id)
        else:
            # Fallback to in-memory storage
            if conversation_id not in conversations:
                return jsonify({'error': 'Conversation not found'}), 404
            
            del conversations[conversation_id]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['DELETE'])
@token_required
def clear_all_conversations():
    """
    Clear All Conversations
    ---
    tags:
      - Conversations
    summary: Delete all conversations
    description: Permanently delete all conversations for the authenticated user. This action cannot be undone. Use with caution.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: All conversations cleared successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        if memory_manager:
            memory_manager.delete_all_conversations()
        else:
            conversations.clear()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>/title', methods=['PUT'])
@token_required
def update_conversation_title(conversation_id):
    """
    Update Conversation Title
    ---
    tags:
      - Conversations
    summary: Update conversation title
    description: Change the title of a conversation. Useful for organizing and identifying conversations.
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: path
        name: conversation_id
        type: string
        required: true
        description: Unique conversation ID
        example: "conv_20240101_120000"
      - in: body
        name: title
        description: New title for the conversation
        required: true
        schema:
          type: object
          required:
            - title
          properties:
            title:
              type: string
              description: New conversation title
              example: "Updated Conversation Title"
    responses:
      200:
        description: Title updated successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            title:
              type: string
              description: Updated title
              example: "Updated Conversation Title"
      400:
        description: Title is required or invalid
        schema:
          type: object
          properties:
            error:
              type: string
              example: Title is required
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      404:
        description: Conversation not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: Conversation not found
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        data = request.json
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
            
            memory_manager.update_conversation_title(conversation_id, new_title)
        else:
            # Fallback to in-memory storage
            if conversation_id not in conversations:
                return jsonify({'error': 'Conversation not found'}), 404
            
            conversations[conversation_id]['title'] = new_title
        
        return jsonify({'success': True, 'title': new_title})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-chat', methods=['POST'])
@token_required
def new_chat():
    """
    Create New Chat
    ---
    tags:
      - Conversations
    summary: Create a new chat conversation
    description: Initialize a new conversation session. Returns a new conversation ID that can be used in subsequent chat requests.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: New conversation created successfully
        schema:
          type: object
          properties:
            conversation_id:
              type: string
              description: Unique conversation ID for the new conversation
              example: "conv_20240101_120000"
            success:
              type: boolean
              example: true
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        conversation_id = generate_conversation_id()
        
        if memory_manager:
            memory_manager.create_conversation(conversation_id, title='New Chat')
        else:
            # Fallback to in-memory storage
            conversations[conversation_id] = {
                'messages': [],
                'title': 'New Chat',
                'created_at': datetime.now().isoformat()
            }
        
        return jsonify({
            'conversation_id': conversation_id,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-model', methods=['GET'])
@token_required
def get_current_model():
    """
    Get Current Model
    ---
    tags:
      - Models
    summary: Get current LLM model
    description: Retrieve the currently active LLM provider and list of available models. The model can be changed per request using the model parameter in the chat endpoint.
    security:
      - Bearer: []
    produces:
      - application/json
    responses:
      200:
        description: Current model information retrieved successfully
        schema:
          type: object
          properties:
            model:
              type: string
              description: Currently active LLM provider
              enum: [openai, gemini, deepseek]
              example: openai
            available_models:
              type: array
              description: List of available LLM providers
              items:
                type: string
                enum: [openai, gemini, deepseek]
              example: [openai, gemini, deepseek]
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        chatbot = get_chatbot()
        return jsonify({
            'model': chatbot.provider_name,
            'available_models': ['openai', 'gemini', 'deepseek']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
@token_required
def search_conversations():
    """
    Search Conversations
    ---
    tags:
      - Conversations
    summary: Search conversations
    description: Search conversations by title or message content. Returns matching conversations ordered by relevance.
    security:
      - Bearer: []
    produces:
      - application/json
    parameters:
      - in: query
        name: q
        type: string
        required: true
        description: Search query string
        example: "Python"
      - in: query
        name: limit
        type: integer
        required: false
        default: 10
        description: Maximum number of results to return
        example: 10
    responses:
      200:
        description: Search completed successfully
        schema:
          type: object
          properties:
            conversations:
              type: array
              description: List of matching conversations
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: Unique conversation ID
                    example: "conv_20240101_120000"
                  title:
                    type: string
                    description: Conversation title
                    example: "Python Questions"
                  created_at:
                    type: string
                    format: date-time
                    description: Conversation creation timestamp
                    example: "2024-01-01T12:00:00"
                  updated_at:
                    type: string
                    format: date-time
                    description: Last update timestamp
                    example: "2024-01-01T13:30:00"
                  message_count:
                    type: integer
                    description: Number of messages in the conversation
                    example: 5
      400:
        description: Search query is required
        schema:
          type: object
          properties:
            error:
              type: string
              example: Search query is required
      401:
        description: Unauthorized - Invalid or missing token
        schema:
          type: object
          properties:
            error:
              type: string
              example: Authentication required. Please provide a valid token.
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error
    """
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        # Parse limit safely
        limit_raw = request.args.get('limit', 10)
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            return jsonify({'error': f'Invalid limit: {limit_raw}. Must be an integer.'}), 400
        
        if memory_manager:
            results = memory_manager.search_conversations(query, limit=limit)
            conv_list = [
                {
                    'id': conv['id'],
                    'title': conv['title'],
                    'created_at': conv['created_at'],
                    'updated_at': conv['updated_at'],
                    'message_count': conv.get('message_count', 0)
                }
                for conv in results
            ]
        else:
            # Fallback: simple search in memory
            conv_list = [
                {
                    'id': conv_id,
                    'title': conv['title'],
                    'created_at': conv['created_at'],
                    'message_count': len(conv['messages'])
                }
                for conv_id, conv in conversations.items()
                if query.lower() in conv['title'].lower() or 
                   any(query.lower() in msg.get('content', '').lower() 
                       for msg in conv['messages'])
            ][:limit]
        
        return jsonify({'conversations': conv_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers to ensure JSON responses for API endpoints
@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors with JSON response."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Bad Request', 'message': str(error)}), 400
    return error

@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors with JSON response."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required. Please provide a valid token.'}), 401
    return error

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors with JSON response."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource.'}), 403
    return error

@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors with JSON response for API endpoints."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found.'}), 404
    return error

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 Method Not Allowed errors."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Method Not Allowed', 'message': 'The requested method is not allowed for this endpoint.'}), 405
    # For non-API paths, redirect to GET or return 405
    # This handles cases where someone tries to POST to a GET-only route
    if request.method == 'POST' and request.path == '/':
        # Someone tried to POST to root - redirect to GET
        return redirect('/', code=303)
    return error

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors with JSON response for API endpoints."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal Server Error', 'message': 'An internal server error occurred.'}), 500
    return error

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions with JSON response for API endpoints."""
    if request.path.startswith('/api/'):
        logger = get_logger('chatbot.app')
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500
    # For non-API paths, log but don't crash - return a generic error page
    logger = get_logger('chatbot.app')
    logger.error(f"Unhandled exception for {request.path}: {error}", exc_info=True)
    # Return a simple error response instead of raising
    from werkzeug.exceptions import InternalServerError
    if isinstance(error, InternalServerError):
        return error
    # For other exceptions on non-API paths, return a 500 error page
    return 'Internal Server Error', 500

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 Chatbot Web UI")
    print("=" * 70)
    print(f"Provider: {Config.LLM_PROVIDER}")
    print(f"Model: {Config.get_llm_model()}")
    print("\nStarting web server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("=" * 70)
    
    # Use stat reloader on Windows to avoid socket errors
    import sys
    use_reloader = True
    reloader_type = 'stat' if sys.platform == 'win32' else 'auto'
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=use_reloader, reloader_type=reloader_type)
    except OSError as e:
        # Handle Windows socket errors during reload
        if sys.platform == 'win32' and '10038' in str(e):
            safe_print("[WARNING] Reloader error detected, restarting without reloader...")
            app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
        else:
            raise

