"""
Integration tests for gateway with chatbot.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from config.config import Config


class TestGatewayWithChatbot:
    """Tests for gateway integration with chatbot."""
    
    @pytest.fixture
    def mock_gateway_provider(self):
        """Create mock gateway provider."""
        with patch('src.llm.router.GATEWAY_AVAILABLE', True):
            with patch('src.llm.router.GatewayProviderWrapper') as mock_wrapper:
                mock_provider = Mock()
                mock_provider.generate_response.return_value = "Gateway response"
                mock_provider.get_provider_name.return_value = "gateway"
                mock_provider.supports_json_mode.return_value = True
                mock_wrapper.return_value = mock_provider
                yield mock_provider
    
    def test_chatbot_uses_gateway_when_enabled(self, mock_gateway_provider):
        """Test that chatbot uses gateway when enabled."""
        with patch.object(Config, 'USE_GATEWAY', True):
            with patch.object(Config, 'GATEWAY_ENABLED', True):
                with patch('src.llm.router.LLMRouter.get_gateway_provider') as mock_get:
                    mock_get.return_value = mock_gateway_provider
                    
                    from src.chatbot import Chatbot
                    
                    # Chatbot should initialize with gateway
                    chatbot = Chatbot(
                        provider_name="gateway",
                        use_fallback=False
                    )
                    
                    # Verify gateway provider was used
                    assert chatbot.llm_provider is not None
                    assert chatbot.llm_provider.get_provider_name() == "gateway"
    
    def test_chatbot_falls_back_to_direct_provider_when_gateway_unavailable(self):
        """Test that chatbot falls back to direct provider when gateway unavailable."""
        with patch.object(Config, 'USE_GATEWAY', True):
            with patch.object(Config, 'GATEWAY_ENABLED', False):
                with patch('src.llm.router.LLMRouter.get_gateway_provider') as mock_get:
                    mock_get.return_value = None
                    
                    with patch('src.llm.router.LLMRouter.get_provider') as mock_direct:
                        mock_provider = Mock()
                        mock_provider.get_provider_name.return_value = "openai"
                        mock_direct.return_value = mock_provider
                        
                        from src.chatbot import Chatbot
                        
                        chatbot = Chatbot(
                            provider_name="openai",
                            use_fallback=False
                        )
                        
                        # Should use direct provider
                        assert chatbot.llm_provider is not None
                        assert chatbot.llm_provider.get_provider_name() == "openai"
    
    def test_llm_router_gateway_provider_method(self):
        """Test LLMRouter.get_gateway_provider method."""
        with patch('src.llm.router.GATEWAY_AVAILABLE', True):
            with patch('src.llm.router.GatewayProviderWrapper') as mock_wrapper:
                with patch.object(Config, 'GATEWAY_ENABLED', True):
                    mock_provider = Mock()
                    mock_wrapper.return_value = mock_provider
                    
                    from src.llm.router import LLMRouter
                    
                    gateway_provider = LLMRouter.get_gateway_provider()
                    
                    assert gateway_provider is not None
                    mock_wrapper.assert_called_once()
    
    def test_llm_router_gateway_provider_returns_none_when_disabled(self):
        """Test that LLMRouter.get_gateway_provider returns None when disabled."""
        with patch.object(Config, 'GATEWAY_ENABLED', False):
            from src.llm.router import LLMRouter
            
            gateway_provider = LLMRouter.get_gateway_provider()
            
            assert gateway_provider is None

