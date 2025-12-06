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
from config.config import Config

app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)

# Global chatbot instance
chatbot_instance = None
conversations = {}  # Store conversation history: {conversation_id: {messages: [], title: str}}

def get_chatbot():
    """Get or create chatbot instance."""
    global chatbot_instance
    if chatbot_instance is None:
        chatbot_instance = Chatbot(
            provider_name=None,  # Use default from Config
            use_fallback=True,
            temperature=0.7,
            max_history=50  # More history for web UI
        )
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
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get or create conversation
        if not conversation_id or conversation_id not in conversations:
            conversation_id = generate_conversation_id()
            conversations[conversation_id] = {
                'messages': [],
                'title': message[:50] + ('...' if len(message) > 50 else ''),
                'created_at': datetime.now().isoformat()
            }
        
        # Add user message to conversation
        conversations[conversation_id]['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Get chatbot response
        chatbot = get_chatbot()
        
        # Restore conversation history for this conversation
        chatbot.conversation_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conversations[conversation_id]['messages'][:-1]  # Exclude current message
        ]
        
        # Get response
        response = chatbot.get_response(message)
        
        # Add assistant response to conversation
        conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update title if it's the first message
        if len(conversations[conversation_id]['messages']) == 2:
            conversations[conversation_id]['title'] = message[:50] + ('...' if len(message) > 50 else '')
        
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
        # Return conversations sorted by creation date (newest first)
        conv_list = [
            {
                'id': conv_id,
                'title': conv['title'],
                'created_at': conv['created_at'],
                'message_count': len(conv['messages'])
            }
            for conv_id, conv in conversations.items()
        ]
        conv_list.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({'conversations': conv_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation."""
    try:
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

