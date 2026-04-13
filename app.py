"""
Flask Web Application for Chatbot UI.

This provides a REST API and serves the web interface for the chatbot.
"""

import sys
from pathlib import Path
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import json
from datetime import datetime
from werkzeug.local import LocalProxy

from config.config import Config
from src.webapp import create_app_runtime, get_app_runtime, safe_print
from src.webapp.conversation_ids import generate_conversation_id
from src.webapp.routes import auth_blueprint, core_blueprint, conversations_blueprint

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

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

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    import time as _time

    REQUEST_COUNT = Counter(
        'http_requests_total', 'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    REQUEST_LATENCY = Histogram(
        'http_request_duration_seconds', 'HTTP request latency',
        ['endpoint'],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    LLM_TOKEN_COST = Counter(
        'llm_token_cost_usd_total', 'Estimated LLM cost in USD',
        ['provider', 'model']
    )
    LLM_TOKEN_COUNT = Counter(
        'llm_tokens_total', 'Total LLM tokens used',
        ['provider', 'model', 'type']
    )
    LLM_ERROR_COUNT = Counter(
        'llm_errors_total', 'LLM provider errors',
        ['provider']
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

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
app.register_blueprint(auth_blueprint)
app.register_blueprint(core_blueprint)
app.register_blueprint(conversations_blueprint)

# Prometheus request instrumentation
if PROMETHEUS_AVAILABLE:
    @app.before_request
    def _start_timer():
        from flask import g
        g._prom_start = _time.time()

    @app.after_request
    def _record_request(response):
        from flask import g
        endpoint = request.endpoint or 'unknown'
        duration = _time.time() - getattr(g, '_prom_start', _time.time())
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
        return response

    @app.route('/metrics')
    def metrics():
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

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

app_runtime = create_app_runtime(
  config=Config,
  chatbot_class=Chatbot,
  memory_manager_class=MemoryManager,
  auth_service_class=AuthService,
  user_service_class=UserService,
  printer=safe_print,
)
app.extensions['chatbot_runtime'] = app_runtime

chatbot_instance = LocalProxy(lambda: get_app_runtime(app_runtime).chatbot_instance)
memory_manager = LocalProxy(lambda: get_app_runtime(app_runtime).memory_manager)
conversations = LocalProxy(lambda: get_app_runtime(app_runtime).conversations)
auth_service = LocalProxy(lambda: get_app_runtime(app_runtime).auth_service)
user_service = LocalProxy(lambda: get_app_runtime(app_runtime).user_service)

def get_chatbot():
    """Get or create chatbot instance with timeout protection."""
    return get_app_runtime(app_runtime).get_chatbot()


def _coerce_json_compatible(value):
    """Return JSON-compatible value, falling back to None for unsupported objects."""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return None

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
        agent_mode = data.get('agent_mode', 'auto').lower()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Validate model
        if model not in ['openai', 'gemini', 'deepseek']:
            return jsonify({'error': f'Invalid model: {model}. Supported models: openai, gemini, deepseek'}), 400
        if agent_mode not in ['auto', 'requirement_sdlc_agent']:
            return jsonify({'error': f'Invalid agent mode: {agent_mode}. Supported agent modes: auto, requirement_sdlc_agent'}), 400
        
        runtime = get_app_runtime(app_runtime)
        title = message[:50] + ('...' if len(message) > 50 else '')
        conversation_id = runtime.ensure_conversation(
            conversation_id=conversation_id,
            title=title,
            generator=generate_conversation_id,
            memory_manager=memory_manager,
        )
        
        # Get chatbot response through request-scoped runtime execution
        chatbot = get_chatbot()
        try:
            execution_result = runtime.execute_chat_request(
                message=message,
                conversation_id=conversation_id,
                model=model,
                agent_mode=agent_mode,
                chatbot=chatbot,
                memory_manager=memory_manager,
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as _llm_err:
            if PROMETHEUS_AVAILABLE:
                LLM_ERROR_COUNT.labels(provider=Config.LLM_PROVIDER).inc()
            raise

        response = execution_result.response

        # Record token cost metrics if usage info is available on the response
        if PROMETHEUS_AVAILABLE and execution_result.usage_info:
            from src.llm.cost_tracker import calculate_cost
            usage = execution_result.usage_info
            provider = usage.get('provider', Config.LLM_PROVIDER)
            usage_model = usage.get('model', Config.get_llm_model())
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            LLM_TOKEN_COUNT.labels(provider=provider, model=usage_model, type='prompt').inc(prompt_tokens)
            LLM_TOKEN_COUNT.labels(provider=provider, model=usage_model, type='completion').inc(completion_tokens)
            cost = calculate_cost(provider, usage_model, prompt_tokens, completion_tokens)
            LLM_TOKEN_COST.labels(provider=provider, model=usage_model).inc(cost)

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
        elif conversation_id in runtime.conversations:
            conversation = runtime.conversations[conversation_id]
            if len(conversation.get('messages', [])) == 2:
                conversation['title'] = title
        
        return jsonify({
            'response': response,
            'conversation_id': conversation_id,
            'agent_mode': agent_mode,
            'ui_actions': _coerce_json_compatible(execution_result.ui_actions),
            'workflow_progress': _coerce_json_compatible(execution_result.workflow_progress),
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

