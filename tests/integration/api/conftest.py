"""
Pytest configuration and fixtures for API integration tests.
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app import app as flask_app
from src.chatbot import Chatbot
from src.services.memory_manager import MemoryManager
from config.config import Config


@pytest.fixture(scope="function")
def test_client():
    """Create a Flask test client."""
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    with flask_app.test_client() as client:
        yield client


@pytest.fixture(scope="function", autouse=True)
def bypass_auth_for_non_auth_api_tests(request, monkeypatch):
    """
    Most API integration tests (chat/conversation/model/search) don't care about auth.
    They expect to hit the endpoints without providing a token.

    Auth-specific tests in `test_auth_api.py` DO validate auth behavior and must not
    bypass authentication.
    """
    nodeid = getattr(request.node, "nodeid", "")
    if "tests/integration/api/test_auth_api.py" in nodeid:
        # Ensure bypass is OFF for auth tests
        monkeypatch.delenv("BYPASS_AUTH", raising=False)
        yield
        return

    # Bypass auth for non-auth API tests
    monkeypatch.setenv("BYPASS_AUTH", "1")
    yield


@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Create MemoryManager with temp database
    memory_manager = MemoryManager(db_path=db_path)
    
    yield memory_manager, db_path
    
    # Cleanup - remove temp database file
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def mock_chatbot():
    """Create a mock Chatbot instance."""
    chatbot = Mock(spec=Chatbot)
    chatbot.provider_name = "openai"
    chatbot.get_response = Mock(return_value="Mocked chatbot response")
    chatbot.switch_provider = Mock(return_value=None)
    chatbot.set_conversation_id = Mock(return_value=None)
    chatbot.load_conversation = Mock(return_value=True)
    chatbot.conversation_history = []
    chatbot.memory_manager = None
    return chatbot


@pytest.fixture(scope="function")
def mock_memory_manager():
    """Create a mock MemoryManager instance."""
    memory_manager = Mock(spec=MemoryManager)
    memory_manager.get_conversation = Mock(return_value=None)
    memory_manager.create_conversation = Mock(return_value=None)
    memory_manager.list_conversations = Mock(return_value=[])
    memory_manager.delete_conversation = Mock(return_value=None)
    memory_manager.delete_all_conversations = Mock(return_value=None)
    memory_manager.update_conversation_title = Mock(return_value=None)
    memory_manager.search_conversations = Mock(return_value=[])
    return memory_manager


@pytest.fixture(scope="function")
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock()
    provider.get_provider_name.return_value = "openai"
    provider.model = "gpt-3.5-turbo"
    provider.generate_response = Mock(return_value="Mocked LLM response")
    provider.supports_json_mode = Mock(return_value=True)
    return provider


@pytest.fixture(scope="function")
def sample_conversation():
    """Create a sample conversation dictionary."""
    return {
        'id': 'test_conv_123',
        'title': 'Test Conversation',
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00',
        'messages': [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ],
        'message_count': 2
    }


@pytest.fixture(scope="function")
def sample_conversations():
    """Create a list of sample conversations."""
    return [
        {
            'id': 'conv_1',
            'title': 'First Conversation',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T01:00:00',
            'message_count': 5
        },
        {
            'id': 'conv_2',
            'title': 'Second Conversation',
            'created_at': '2024-01-02T00:00:00',
            'updated_at': '2024-01-02T02:00:00',
            'message_count': 3
        }
    ]


@pytest.fixture(scope="function", autouse=True)
def reset_global_chatbot():
    """Reset global chatbot instance before each test."""
    import app
    app.chatbot_instance = None
    yield
    app.chatbot_instance = None


@pytest.fixture(scope="function", autouse=True)
def reset_global_memory_manager():
    """Reset global memory manager before each test."""
    import app
    original_memory_manager = app.memory_manager
    yield
    app.memory_manager = original_memory_manager


# Auth bypass is controlled via BYPASS_AUTH env var (see fixture above).