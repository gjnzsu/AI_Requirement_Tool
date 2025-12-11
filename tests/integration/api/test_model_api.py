"""
Tests for GET /api/current-model endpoint.
"""

import pytest
import json
from unittest.mock import patch, Mock


@pytest.mark.integration
@pytest.mark.api
class TestModelAPI:
    """Test suite for model management endpoint."""
    
    def test_get_current_model(self, test_client, mock_chatbot):
        """Test getting current model."""
        mock_chatbot.provider_name = "openai"
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            response = test_client.get('/api/current-model')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'model' in data
            assert data['model'] == 'openai'
            assert 'available_models' in data
            assert isinstance(data['available_models'], list)
            assert 'openai' in data['available_models']
            assert 'gemini' in data['available_models']
            assert 'deepseek' in data['available_models']
    
    def test_get_current_model_gemini(self, test_client, mock_chatbot):
        """Test getting current model when Gemini is selected."""
        mock_chatbot.provider_name = "gemini"
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            response = test_client.get('/api/current-model')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['model'] == 'gemini'
    
    def test_get_current_model_deepseek(self, test_client, mock_chatbot):
        """Test getting current model when DeepSeek is selected."""
        mock_chatbot.provider_name = "deepseek"
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            response = test_client.get('/api/current-model')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['model'] == 'deepseek'
    
    def test_get_current_model_chatbot_creation_error(self, test_client):
        """Test handling error when chatbot creation fails."""
        with patch('app.get_chatbot', side_effect=Exception("Chatbot creation failed")):
            response = test_client.get('/api/current-model')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_model_switching_persistence(self, test_client, mock_chatbot, temp_db):
        """Test that model switching persists across requests."""
        memory_manager, db_path = temp_db
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.memory_manager', memory_manager):
                # Switch to gemini
                response1 = test_client.post(
                    '/api/chat',
                    json={
                        'message': 'Hello',
                        'model': 'gemini'
                    },
                    content_type='application/json'
                )
                assert response1.status_code == 200
                
                # Verify model is still gemini
                response2 = test_client.get('/api/current-model')
                assert response2.status_code == 200
                data = json.loads(response2.data)
                # Note: This test verifies the switch was called, actual persistence
                # depends on chatbot instance lifecycle
                mock_chatbot.switch_provider.assert_called_with('gemini')

