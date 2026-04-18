"""
Tests for POST /api/chat endpoint.
"""

import pytest
import json
from unittest.mock import patch, Mock


def build_runtime_mock(
    *,
    conversation_id='conv-123',
    response_text="Mocked chatbot response",
    ui_actions=None,
    workflow_progress=None,
):
    runtime = Mock()
    runtime.ensure_conversation.return_value = conversation_id
    runtime.enqueue_async_chat_request_if_needed.return_value = None
    runtime.execute_chat_request.return_value = Mock(
        response=response_text,
        conversation_id=conversation_id,
        usage_info=None,
        ui_actions=ui_actions,
        workflow_progress=workflow_progress,
    )
    return runtime


@pytest.mark.integration
@pytest.mark.api
class TestChatAPI:
    """Test suite for POST /api/chat endpoint."""
    
    def test_chat_success(self, test_client, mock_chatbot, temp_db):
        """Test successful chat request."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        
        memory_manager.get_conversation = Mock(return_value=None)
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
                    assert 'agent_mode' in data
                    assert 'timestamp' in data
                    assert data['response'] == "Mocked chatbot response"
                    assert data['agent_mode'] == 'auto'
                    runtime.enqueue_async_chat_request_if_needed.assert_called_once()
                    runtime.execute_chat_request.assert_called_once()
    
    def test_chat_with_conversation_id(self, test_client, mock_chatbot, temp_db, sample_conversation):
        """Test chat with existing conversation ID."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock(conversation_id=sample_conversation['id'])
        
        # Create conversation in memory
        memory_manager.create_conversation(
            sample_conversation['id'],
            title=sample_conversation['title']
        )
        memory_manager.get_conversation = Mock(return_value=sample_conversation)
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
                    runtime.ensure_conversation.assert_called_once()
    
    def test_chat_provider_switching_openai(self, test_client, mock_chatbot, temp_db):
        """Test switching to OpenAI provider."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        # Set provider to something different so switch_provider will be called
        mock_chatbot.provider_name = "gemini"
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
                    assert runtime.execute_chat_request.call_args.kwargs['model'] == 'openai'
    
    def test_chat_provider_switching_gemini(self, test_client, mock_chatbot, temp_db):
        """Test switching to Gemini provider."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
                    assert runtime.execute_chat_request.call_args.kwargs['model'] == 'gemini'
    
    def test_chat_provider_switching_deepseek(self, test_client, mock_chatbot, temp_db):
        """Test switching to DeepSeek provider."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
                    assert runtime.execute_chat_request.call_args.kwargs['model'] == 'deepseek'
    
    def test_chat_invalid_model(self, test_client, mock_chatbot, temp_db):
        """Test chat with invalid model name."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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

    def test_chat_invalid_agent_mode(self, test_client, mock_chatbot, temp_db):
        """Test chat with invalid agent mode."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()

        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={
                            'message': 'Hello',
                            'agent_mode': 'invalid-agent-mode'
                        },
                        content_type='application/json'
                    )

                    assert response.status_code == 400
                    data = json.loads(response.data)
                    assert 'error' in data
                    assert 'agent mode' in data['error'].lower() or 'invalid' in data['error'].lower()

    def test_chat_explicit_requirement_sdlc_agent_mode(self, test_client, mock_chatbot, temp_db):
        """Test chat request with explicit Requirement SDLC Agent mode."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock(
            ui_actions=[
                {"label": "Approve", "value": "approve", "kind": "primary"},
                {"label": "Cancel", "value": "cancel", "kind": "secondary"},
            ],
            workflow_progress=[
                {"step": "jira", "label": "Create Jira", "status": "completed"},
            ],
        )

        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={
                            'message': 'Help me turn this into a requirement',
                            'agent_mode': 'requirement_sdlc_agent'
                        },
                        content_type='application/json'
                    )

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['agent_mode'] == 'requirement_sdlc_agent'
                    assert data['ui_actions'] == [
                        {"label": "Approve", "value": "approve", "kind": "primary"},
                        {"label": "Cancel", "value": "cancel", "kind": "secondary"},
                    ]
                    assert data['workflow_progress'] == [
                        {"step": "jira", "label": "Create Jira", "status": "completed"},
                    ]
                    assert runtime.execute_chat_request.call_args.kwargs['agent_mode'] == 'requirement_sdlc_agent'
    
    def test_chat_empty_message(self, test_client, mock_chatbot, temp_db):
        """Test chat with empty message."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
        runtime = build_runtime_mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
        runtime = build_runtime_mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={'message': 'Test message'},
                        content_type='application/json'
                    )

                    assert response.status_code == 200
                    runtime.ensure_conversation.assert_called_once()
                    runtime.enqueue_async_chat_request_if_needed.assert_called_once()
                    runtime.execute_chat_request.assert_called_once()

    def test_chat_coze_agent_request_returns_202_and_skips_sync_execution(self, test_client, mock_chatbot, temp_db):
        """Test Coze-routed requests enqueue an async job instead of executing synchronously."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock(conversation_id='conv-async-123')
        runtime.enqueue_async_chat_request_if_needed.return_value = {
            'job_id': 'job-123',
            'status': 'queued',
        }

        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={'message': 'Give me the AI daily report'},
                        content_type='application/json'
                    )

                    assert response.status_code == 202
                    data = json.loads(response.data)
                    assert data == {
                        'job_id': 'job-123',
                        'status': 'queued',
                        'conversation_id': 'conv-async-123'
                    }
                    runtime.enqueue_async_chat_request_if_needed.assert_called_once()
                    runtime.execute_chat_request.assert_not_called()

    def test_chat_ensures_conversation_before_async_enqueue(self, test_client, mock_chatbot, temp_db):
        """Test conversation creation happens before the async enqueue decision."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock(conversation_id='conv-async-order')
        call_order = []

        def record_ensure(*args, **kwargs):
            call_order.append('ensure_conversation')
            return 'conv-async-order'

        def record_enqueue(*args, **kwargs):
            call_order.append('enqueue_async_chat_request_if_needed')
            return {'job_id': 'job-ordered', 'status': 'queued'}

        runtime.ensure_conversation.side_effect = record_ensure
        runtime.enqueue_async_chat_request_if_needed.side_effect = record_enqueue

        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={'message': 'Share AI news for today'},
                        content_type='application/json'
                    )

                    assert response.status_code == 202
                    assert call_order == [
                        'ensure_conversation',
                        'enqueue_async_chat_request_if_needed',
                    ]

    def test_chat_async_path_disabled_falls_back_to_sync_execution(self, test_client, mock_chatbot, temp_db):
        """Test async-disabled behavior still returns the normal synchronous response."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock(response_text='Synchronous fallback response')
        runtime.enqueue_async_chat_request_if_needed.return_value = None

        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    with patch('app.Config.ASYNC_COZE_ENABLED', False):
                        response = test_client.post(
                            '/api/chat',
                            json={'message': 'Give me the AI daily report'},
                            content_type='application/json'
                        )

                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data['response'] == 'Synchronous fallback response'
                        runtime.enqueue_async_chat_request_if_needed.assert_called_once()
                        runtime.execute_chat_request.assert_called_once()

    def test_chat_async_preflight_value_error_returns_400(self, test_client, mock_chatbot, temp_db):
        """Test ValueError during async preflight preserves the existing 400 behavior."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        runtime.enqueue_async_chat_request_if_needed.side_effect = ValueError("Invalid provider")

        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={'message': 'Hello'},
                        content_type='application/json'
                    )

                    assert response.status_code == 400
                    data = json.loads(response.data)
                    assert data['error'] == 'Invalid provider'
                    runtime.execute_chat_request.assert_not_called()
    
    def test_chat_llm_failure(self, test_client, mock_chatbot, temp_db):
        """Test handling of LLM provider failures."""
        memory_manager, db_path = temp_db
        runtime = build_runtime_mock()
        mock_chatbot.get_response.side_effect = Exception("LLM API error")
        runtime.execute_chat_request.side_effect = Exception("LLM API error")
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
        runtime = build_runtime_mock()
        # Set provider to something different so switch_provider will be called
        mock_chatbot.provider_name = "gemini"
        mock_chatbot.switch_provider.side_effect = ValueError("Invalid provider")
        runtime.execute_chat_request.side_effect = ValueError("Invalid provider")
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
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
        runtime = build_runtime_mock(conversation_id='conv-title')
        memory_manager.get_conversation = Mock(return_value={'messages': [{}, {}], 'title': 'Old Title'})
        memory_manager.update_conversation_title = Mock()
        
        with patch('app.get_chatbot', return_value=mock_chatbot):
            with patch('app.get_app_runtime', return_value=runtime):
                with patch('app.memory_manager', memory_manager):
                    response = test_client.post(
                        '/api/chat',
                        json={'message': 'This is a test message'},
                        content_type='application/json'
                    )

                    assert response.status_code == 200
                    memory_manager.update_conversation_title.assert_called_once()



