"""
Pytest configuration and shared fixtures for all tests.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path for all tests
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from config.config import Config


@pytest.fixture(scope="function")
def event_loop():
    """
    Create a new event loop per test for async tests.
    Avoids 'Runner.run() cannot be called from a running event loop' when
    running with pytest-xdist (parallel workers).
    Do not close the loop in teardown - pytest-asyncio's runner manages
    lifecycle; closing here causes "Cannot run the event loop while another
    loop is running" in worker teardown.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Intentionally do not loop.close() - let pytest-asyncio clean up
    # to avoid conflicts when running with pytest-xdist


@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root path."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def mock_config():
    """Provide a mock Config object for testing."""
    config = Mock(spec=Config)
    config.JIRA_URL = "https://test.atlassian.net"
    config.JIRA_EMAIL = "test@example.com"
    config.JIRA_API_TOKEN = "test-token"
    config.JIRA_PROJECT_KEY = "TEST"
    config.OPENAI_API_KEY = "test-openai-key"
    config.GEMINI_API_KEY = "test-gemini-key"
    config.LLM_PROVIDER = "openai"
    config.USE_MCP = True
    config.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
    config.CONFLUENCE_SPACE_KEY = "TEST"
    return config


@pytest.fixture(scope="function")
def mock_mcp_client():
    """Provide a mock MCP client for testing."""
    client = AsyncMock()
    client._initialized = True
    client.tools = {
        'create_jira_issue': {
            'name': 'create_jira_issue',
            'description': 'Create a Jira issue',
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'summary': {'type': 'string'},
                    'description': {'type': 'string'},
                    'project_key': {'type': 'string'}
                },
                'required': ['summary', 'project_key']
            }
        }
    }
    return client


@pytest.fixture(scope="function")
def mock_llm_provider():
    """Provide a mock LLM provider for testing."""
    provider = Mock()
    provider.get_provider_name.return_value = "openai"
    provider.model = "gpt-4"
    provider.invoke = AsyncMock(return_value="Mocked LLM response")
    provider.generate_response = Mock(return_value="Mocked LLM response")
    return provider


@pytest.fixture(scope="function")
def mock_chatbot():
    """Provide a mock Chatbot for testing without API calls."""
    from unittest.mock import Mock, PropertyMock
    
    chatbot = Mock()
    chatbot.get_response = Mock(return_value="Mocked chatbot response")
    chatbot.memory_manager = Mock()
    chatbot.conversation_history = []
    chatbot.set_conversation_id = Mock()
    chatbot.load_conversation = Mock(return_value=True)
    
    # Mock memory_manager methods
    chatbot.memory_manager.get_conversation = Mock(return_value={
        'id': 'test_conv',
        'title': 'Test',
        'messages': [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi'}
        ]
    })
    chatbot.memory_manager.add_message = Mock()
    chatbot.memory_manager.create_conversation = Mock()
    
    return chatbot

