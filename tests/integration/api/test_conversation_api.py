"""
Tests for conversation management API endpoints.
"""

import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.integration
@pytest.mark.api
class TestConversationAPI:
    """Test suite for conversation management endpoints."""
    
    def test_list_conversations_empty(self, test_client, temp_db):
        """Test listing conversations when none exist."""
        memory_manager, db_path = temp_db
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/conversations')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data
            assert isinstance(data['conversations'], list)
            assert len(data['conversations']) == 0
    
    def test_list_conversations_with_data(self, test_client, temp_db, sample_conversations):
        """Test listing conversations with existing data."""
        memory_manager, db_path = temp_db
        memory_manager.list_conversations = Mock(return_value=sample_conversations)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/conversations')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data
            assert len(data['conversations']) == 2
            assert data['conversations'][0]['id'] == sample_conversations[0]['id']
    
    def test_get_conversation_exists(self, test_client, temp_db, sample_conversation):
        """Test getting a specific conversation that exists."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get(f"/api/conversations/{sample_conversation['id']}")
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversation' in data
            assert data['conversation']['id'] == sample_conversation['id']
            assert data['conversation']['title'] == sample_conversation['title']
    
    def test_get_conversation_not_found(self, test_client, temp_db):
        """Test getting a conversation that doesn't exist."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=None)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/conversations/nonexistent_id')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
            assert 'not found' in data['error'].lower()
    
    def test_delete_conversation_exists(self, test_client, temp_db, sample_conversation):
        """Test deleting a conversation that exists."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        memory_manager.delete_conversation = Mock(return_value=None)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.delete(f"/api/conversations/{sample_conversation['id']}")
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get('success') is True
            memory_manager.delete_conversation.assert_called_once_with(sample_conversation['id'])
    
    def test_delete_conversation_not_found(self, test_client, temp_db):
        """Test deleting a conversation that doesn't exist."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=None)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.delete('/api/conversations/nonexistent_id')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_clear_all_conversations(self, test_client, temp_db):
        """Test clearing all conversations."""
        memory_manager, db_path = temp_db
        memory_manager.delete_all_conversations = Mock(return_value=None)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.delete('/api/conversations')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get('success') is True
            memory_manager.delete_all_conversations.assert_called_once()
    
    def test_update_conversation_title(self, test_client, temp_db, sample_conversation):
        """Test updating conversation title."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        memory_manager.update_conversation_title = Mock(return_value=None)
        
        new_title = "Updated Title"
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.put(
                f"/api/conversations/{sample_conversation['id']}/title",
                json={'title': new_title},
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get('success') is True
            assert data.get('title') == new_title
            memory_manager.update_conversation_title.assert_called_once_with(
                sample_conversation['id'],
                new_title
            )
    
    def test_update_conversation_title_empty(self, test_client, temp_db, sample_conversation):
        """Test updating conversation title with empty string."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.put(
                f"/api/conversations/{sample_conversation['id']}/title",
                json={'title': ''},
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert 'required' in data['error'].lower()
    
    def test_update_conversation_title_not_found(self, test_client, temp_db):
        """Test updating title of non-existent conversation."""
        memory_manager, db_path = temp_db
        memory_manager.get_conversation = Mock(return_value=None)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.put(
                '/api/conversations/nonexistent_id/title',
                json={'title': 'New Title'},
                content_type='application/json'
            )
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_create_new_chat(self, test_client, temp_db):
        """Test creating a new chat conversation."""
        memory_manager, db_path = temp_db
        memory_manager.create_conversation = Mock(return_value=None)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.post('/api/new-chat')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversation_id' in data
            assert data.get('success') is True
            assert memory_manager.create_conversation.called
    
    def test_conversation_persistence_across_calls(self, test_client, temp_db, sample_conversation):
        """Test that conversations persist across multiple API calls."""
        memory_manager, db_path = temp_db
        
        # Create conversation
        memory_manager.create_conversation(
            sample_conversation['id'],
            title=sample_conversation['title']
        )
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        
        with patch('app.memory_manager', memory_manager):
            # First call - get conversation
            response1 = test_client.get(f"/api/conversations/{sample_conversation['id']}")
            assert response1.status_code == 200
            
            # Second call - should still exist
            response2 = test_client.get(f"/api/conversations/{sample_conversation['id']}")
            assert response2.status_code == 200
            
            data1 = json.loads(response1.data)
            data2 = json.loads(response2.data)
            assert data1['conversation']['id'] == data2['conversation']['id']

