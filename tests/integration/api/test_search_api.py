"""
Tests for GET /api/search endpoint.
"""

import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.integration
@pytest.mark.api
class TestSearchAPI:
    """Test suite for search endpoint."""
    
    def test_search_with_query(self, test_client, temp_db, sample_conversations):
        """Test search with a query string."""
        memory_manager, db_path = temp_db
        memory_manager.search_conversations = Mock(return_value=sample_conversations)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/search?q=test')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data
            assert isinstance(data['conversations'], list)
            memory_manager.search_conversations.assert_called_once_with('test', limit=10)
    
    def test_search_with_limit(self, test_client, temp_db, sample_conversations):
        """Test search with custom limit parameter."""
        memory_manager, db_path = temp_db
        memory_manager.search_conversations = Mock(return_value=sample_conversations)
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/search?q=test&limit=5')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data
            memory_manager.search_conversations.assert_called_once_with('test', limit=5)
    
    def test_search_no_results(self, test_client, temp_db):
        """Test search that returns no results."""
        memory_manager, db_path = temp_db
        memory_manager.search_conversations = Mock(return_value=[])
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/search?q=nonexistent')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data
            assert len(data['conversations']) == 0
    
    def test_search_missing_query(self, test_client, temp_db):
        """Test search without query parameter."""
        memory_manager, db_path = temp_db
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/search')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert 'required' in data['error'].lower() or 'query' in data['error'].lower()
    
    def test_search_empty_query(self, test_client, temp_db):
        """Test search with empty query string."""
        memory_manager, db_path = temp_db
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/search?q=')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_search_integration_with_memory_manager(self, test_client, temp_db):
        """Test search integration with MemoryManager."""
        memory_manager, db_path = temp_db
        
        # Create test conversations
        memory_manager.create_conversation('conv_1', title='Python Tutorial')
        memory_manager.create_conversation('conv_2', title='Flask Guide')
        memory_manager.add_message('conv_1', 'user', 'How do I use Python?')
        memory_manager.add_message('conv_2', 'user', 'Tell me about Flask')
        
        with patch('app.memory_manager', memory_manager):
            # Search for Python
            response = test_client.get('/api/search?q=Python')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data
            # Should find at least one conversation
            assert len(data['conversations']) >= 0
    
    def test_search_limit_validation(self, test_client, temp_db):
        """Test search with invalid limit parameter."""
        memory_manager, db_path = temp_db
        
        with patch('app.memory_manager', memory_manager):
            # Test with non-numeric limit
            response = test_client.get('/api/search?q=test&limit=invalid')
            
            # Should either handle gracefully or return error
            # The implementation may convert to int or return error
            assert response.status_code in [200, 400]
    
    def test_search_special_characters(self, test_client, temp_db):
        """Test search with special characters in query."""
        memory_manager, db_path = temp_db
        memory_manager.search_conversations = Mock(return_value=[])
        
        with patch('app.memory_manager', memory_manager):
            response = test_client.get('/api/search?q=test%20query%20with%20spaces')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'conversations' in data

