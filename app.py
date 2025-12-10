"""
Flask Web Application for Chatbot UI.

This provides a REST API and serves the web interface for the chatbot.
"""

import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.chatbot import Chatbot
from src.services.memory_manager import MemoryManager
from config.config import Config

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)

# Global chatbot instance
chatbot_instance = None
memory_manager = None
conversations = {}  # Fallback in-memory storage when persistent memory is disabled

# Initialize memory manager if enabled
if Config.USE_PERSISTENT_MEMORY:
    try:
        memory_manager = MemoryManager(
            db_path=Config.MEMORY_DB_PATH,
            max_context_messages=Config.MAX_CONTEXT_MESSAGES
        )
        print("✓ Initialized Memory Manager for web app")
    except Exception as e:
        print(f"⚠ Failed to initialize Memory Manager: {e}")
        memory_manager = None
        print("   Falling back to in-memory storage")
else:
    memory_manager = None
    print("⚠ Persistent memory disabled (USE_PERSISTENT_MEMORY=false)")

def get_chatbot():
    """Get or create chatbot instance."""
    global chatbot_instance
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
        
        chatbot_instance = Chatbot(
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

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        model = data.get('model', 'openai').lower()  # Get model from request, default to openai
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Validate model
        if model not in ['openai', 'gemini']:
            return jsonify({'error': f'Invalid model: {model}. Supported models: openai, gemini'}), 400
        
        # Get or create conversation
        if not conversation_id or (memory_manager and not memory_manager.get_conversation(conversation_id)):
            conversation_id = generate_conversation_id()
            title = message[:50] + ('...' if len(message) > 50 else '')
            
            if memory_manager:
                memory_manager.create_conversation(conversation_id, title=title)
        
        # Get chatbot response
        chatbot = get_chatbot()
        
        # Switch provider if different from current
        if chatbot.provider_name != model:
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get list of all conversations."""
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
def get_conversation(conversation_id):
    """Get a specific conversation."""
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
def delete_conversation(conversation_id):
    """Delete a conversation."""
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
def clear_all_conversations():
    """Clear all conversations."""
    try:
        if memory_manager:
            memory_manager.delete_all_conversations()
        else:
            conversations.clear()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>/title', methods=['PUT'])
def update_conversation_title(conversation_id):
    """Update conversation title."""
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
def new_chat():
    """Create a new chat conversation."""
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
def get_current_model():
    """Get the current model being used by the chatbot."""
    try:
        chatbot = get_chatbot()
        return jsonify({
            'model': chatbot.provider_name,
            'available_models': ['openai', 'gemini']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_conversations():
    """Search conversations."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        limit = int(request.args.get('limit', 10))
        
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

if __name__ == '__main__':
    print("=" * 70)
    print("🤖 Chatbot Web UI")
    print("=" * 70)
    print(f"Provider: {Config.LLM_PROVIDER}")
    print(f"Model: {Config.get_llm_model()}")
    print("\nStarting web server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

