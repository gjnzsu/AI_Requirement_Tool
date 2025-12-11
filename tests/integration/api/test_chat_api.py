"""
Tests for POST /api/chat endpoint.
"""

import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.integration
@pytest.mark.api
class TestChatAPI:
    """Test suite for POST /api/chat endpoint."""
    
    def test_chat_success(self, test_client, mock_chatbot, temp_db):
        """Test successful chat request."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={'message': 'Hello, how are you?'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'response' in data
                assert 'conversation_id' in data
                assert 'timestamp' in data
                assert data['response'] == "Mocked chatbot response"
    
    def test_chat_with_conversation_id(self, test_client, mock_chatbot, temp_db, sample_conversation):
        """Test chat with existing conversation ID."""
        memory_manager, db_path = temp_db
        
        # Create conversation in memory
        memory_manager.create_conversation(
            sample_conversation['id'],
            title=sample_conversation['title']
        )
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Continue our conversation',
                        'conversation_id': sample_conversation['id']
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['conversation_id'] == sample_conversation['id']
                mock_chatbot.load_conversation.assert_called_once_with(sample_conversation['id'])
    
    def test_chat_provider_switching_openai(self, test_client, mock_chatbot, temp_db):
        """Test switching to OpenAI provider."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Hello',
                        'model': 'openai'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                mock_chatbot.switch_provider.assert_called_once_with('openai')
    
    def test_chat_provider_switching_gemini(self, test_client, mock_chatbot, temp_db):
        """Test switching to Gemini provider."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Hello',
                        'model': 'gemini'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                mock_chatbot.switch_provider.assert_called_once_with('gemini')
    
    def test_chat_provider_switching_deepseek(self, test_client, mock_chatbot, temp_db):
        """Test switching to DeepSeek provider."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Hello',
                        'model': 'deepseek'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                mock_chatbot.switch_provider.assert_called_once_with('deepseek')
    
    def test_chat_invalid_model(self, test_client, mock_chatbot, temp_db):
        """Test chat with invalid model name."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Hello',
                        'model': 'invalid-model'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'error' in data
                assert 'invalid-model' in data['error'].lower() or 'invalid' in data['error'].lower()
    
    def test_chat_empty_message(self, test_client, mock_chatbot, temp_db):
        """Test chat with empty message."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={'message': ''},
                    content_type='application/json'
                )
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'error' in data
                assert 'required' in data['error'].lower() or 'empty' in data['error'].lower()
    
    def test_chat_missing_message(self, test_client, mock_chatbot, temp_db):
        """Test chat request without message field."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={},
                    content_type='application/json'
                )
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'error' in data
    
    def test_chat_memory_persistence(self, test_client, mock_chatbot, temp_db):
        """Test that chat messages are persisted to memory."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={'message': 'Test message'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                conversation_id = data['conversation_id']
                
                # Verify conversation was created
                conversation = memory_manager.get_conversation(conversation_id)
                assert conversation is not None
    
    def test_chat_llm_failure(self, test_client, mock_chatbot, temp_db):
        """Test handling of LLM provider failures."""
        memory_manager, db_path = temp_db
        mock_chatbot.get_response.side_effect = Exception("LLM API error")
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={'message': 'Hello'},
                    content_type='application/json'
                )
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert 'error' in data
    
    def test_chat_provider_switch_failure(self, test_client, mock_chatbot, temp_db):
        """Test handling of provider switch failures."""
        memory_manager, db_path = temp_db
        mock_chatbot.switch_provider.side_effect = ValueError("Invalid provider")
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Hello',
                        'model': 'openai'
                    },
                    content_type='application/json'
                )
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'error' in data
    
    def test_chat_conversation_title_update(self, test_client, mock_chatbot, temp_db):
        """Test that conversation title is updated after first message."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                response = test_client.post(
                    '/api/chat',
                    json={'message': 'This is a test message'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                conversation_id = data['conversation_id']
                
                # Verify title was set
                conversation = memory_manager.get_conversation(conversation_id)
                if conversation:
                    assert 'title' in conversation
                    assert len(conversation['title']) > 0

