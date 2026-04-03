"""Conversation management routes for the Flask web app."""

from datetime import datetime

from flask import Blueprint, jsonify, request

from src.webapp import get_app_runtime
from src.webapp.conversation_ids import generate_conversation_id

try:
    from src.auth import token_required
except ImportError:
    token_required = lambda f: f


conversations_blueprint = Blueprint("conversations", __name__)


@conversations_blueprint.route('/api/conversations', methods=['GET'])
@token_required
def get_conversations():
    """List all conversations for the current storage backend."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
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
            conv_list.sort(key=lambda item: item.get('updated_at', item['created_at']), reverse=True)

        return jsonify({'conversations': conv_list})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@conversations_blueprint.route('/api/conversations/<conversation_id>', methods=['GET'])
@token_required
def get_conversation(conversation_id):
    """Get a specific conversation by ID."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404

            return jsonify({'conversation': conversation})

        if conversation_id not in conversations:
            return jsonify({'error': 'Conversation not found'}), 404

        return jsonify({'conversation': conversations[conversation_id]})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@conversations_blueprint.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@token_required
def delete_conversation(conversation_id):
    """Delete a conversation by ID."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
            conversation = memory_manager.get_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404

            memory_manager.delete_conversation(conversation_id)
        else:
            if conversation_id not in conversations:
                return jsonify({'error': 'Conversation not found'}), 404

            del conversations[conversation_id]

        return jsonify({'success': True})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@conversations_blueprint.route('/api/conversations', methods=['DELETE'])
@token_required
def clear_all_conversations():
    """Delete all conversations."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations

        if memory_manager:
            memory_manager.delete_all_conversations()
        else:
            conversations.clear()

        return jsonify({'success': True})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@conversations_blueprint.route('/api/conversations/<conversation_id>/title', methods=['PUT'])
@token_required
def update_conversation_title(conversation_id):
    """Update a conversation title."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations
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
            if conversation_id not in conversations:
                return jsonify({'error': 'Conversation not found'}), 404

            conversations[conversation_id]['title'] = new_title

        return jsonify({'success': True, 'title': new_title})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@conversations_blueprint.route('/api/new-chat', methods=['POST'])
@token_required
def new_chat():
    """Create a new conversation and return its ID."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations
        conversation_id = generate_conversation_id()

        if memory_manager:
            memory_manager.create_conversation(conversation_id, title='New Chat')
        else:
            conversations[conversation_id] = {
                'messages': [],
                'title': 'New Chat',
                'created_at': datetime.now().isoformat()
            }

        return jsonify({'conversation_id': conversation_id, 'success': True})
    except Exception as error:
        return jsonify({'error': str(error)}), 500


@conversations_blueprint.route('/api/search', methods=['GET'])
@token_required
def search_conversations():
    """Search stored conversations by title or message content."""
    try:
        runtime = get_app_runtime()
        memory_manager = runtime.memory_manager
        conversations = runtime.conversations
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'error': 'Search query is required'}), 400

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
            conv_list = [
                {
                    'id': conv_id,
                    'title': conv['title'],
                    'created_at': conv['created_at'],
                    'message_count': len(conv['messages'])
                }
                for conv_id, conv in conversations.items()
                if query.lower() in conv['title'].lower() or any(
                    query.lower() in msg.get('content', '').lower()
                    for msg in conv['messages']
                )
            ][:limit]

        return jsonify({'conversations': conv_list})
    except Exception as error:
        return jsonify({'error': str(error)}), 500
