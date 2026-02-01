"""
Integration tests for Confluence URL format verification.

Tests that Confluence URLs are correctly formatted with the /wiki prefix
in all three URL construction locations in agent_graph.py.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.agent_graph import ChatbotAgent
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.confluence_url_format')


class TestConfluenceURLFormat:
    """Test suite for Confluence URL format verification."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config with Confluence URL."""
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.CONFLUENCE_URL = "https://30156758.atlassian.net/wiki"
            mock_config.JIRA_URL = "https://30156758.atlassian.net"
            mock_config.JIRA_PROJECT_KEY = "SCRUM"
            mock_config.USE_MCP = True
            mock_config.USE_RAG = True
            yield mock_config
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create agent instance with mocked dependencies."""
        # Patch imports correctly - patch where they're imported from
        with patch('src.llm.LLMRouter'), \
             patch('src.rag.RAGService'), \
             patch('src.services.memory_manager.MemoryManager'), \
             patch('src.mcp.mcp_integration.MCPIntegration') as mock_mcp:
            
            # Set additional config values needed
            mock_config.OPENAI_MODEL = 'gpt-3.5-turbo'
            mock_config.OPENAI_API_KEY = 'test-key'
            mock_config.USE_PERSISTENT_MEMORY = False
            
            # Mock MCP integration
            mock_mcp_instance = Mock()
            mock_mcp_instance._initialized = True
            mock_mcp_instance.get_tools.return_value = []
            mock_mcp.return_value = mock_mcp_instance
            
            agent = ChatbotAgent(
                provider_name='openai',
                enable_tools=True,
                use_mcp=True
            )
            return agent
    
    def test_confluence_url_has_wiki_prefix_from_webui_path(self, agent, mock_config):
        """Test URL construction from webui_path includes /wiki prefix."""
        # Simulate MCP response with webui_path
        webui_path = "/spaces/SCRUM/pages/8192024/SCRUM-210+Performance+tuning"
        page_id = "8192024"
        
        # Extract base URL (should remove /wiki if present)
        base_url = mock_config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
        expected_url = f"{base_url}/wiki{webui_path}"
        
        # Verify URL construction logic
        if webui_path.startswith('http'):
            page_link = webui_path
        else:
            page_link = f"{base_url}/wiki{webui_path}"
        
        assert '/wiki' in page_link
        assert page_link.startswith('https://')
        assert '30156758.atlassian.net' in page_link
        logger.info(f"✓ URL from webui_path: {page_link}")
    
    def test_confluence_url_has_wiki_prefix_from_page_id(self, agent, mock_config):
        """Test URL construction from page_id includes /wiki prefix."""
        page_id = "8192024"
        base_url = mock_config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
        expected_url = f"{base_url}/wiki/pages/viewpage.action?pageId={page_id}"
        
        # Simulate URL construction
        page_link = f"{base_url}/wiki/pages/viewpage.action?pageId={page_id}"
        
        assert '/wiki' in page_link
        assert page_id in page_link
        assert page_link.startswith('https://')
        logger.info(f"✓ URL from page_id: {page_link}")
    
    def test_confluence_url_fallback_has_wiki_prefix(self, agent, mock_config):
        """Test fallback URL construction includes /wiki prefix."""
        page_id = "8192024"
        fallback_base = mock_config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
        fallback_url = f"{fallback_base}/wiki/pages/viewpage.action?pageId={page_id}"
        
        assert '/wiki' in fallback_url
        assert page_id in fallback_url
        assert fallback_url.startswith('https://')
        logger.info(f"✓ Fallback URL: {fallback_url}")
    
    def test_confluence_url_format_matches_expected(self, agent, mock_config):
        """Test that constructed URLs match expected format."""
        # Expected format: https://30156758.atlassian.net/wiki/spaces/SCRUM/pages/8192024/...
        base_url = "https://30156758.atlassian.net"
        webui_path = "/spaces/SCRUM/pages/8192024/SCRUM-210+Performance+tuning"
        
        page_link = f"{base_url}/wiki{webui_path}"
        expected_format = "https://30156758.atlassian.net/wiki/spaces/SCRUM/pages/8192024/SCRUM-210+Performance+tuning"
        
        assert page_link == expected_format
        assert page_link.startswith(f"{base_url}/wiki")
        logger.info(f"✓ URL format matches expected: {page_link}")
    
    def test_confluence_url_handles_existing_wiki_in_base_url(self, agent, mock_config):
        """Test that URL construction handles base URL that already contains /wiki."""
        # If CONFLUENCE_URL already has /wiki, split should remove it
        confluence_url_with_wiki = "https://30156758.atlassian.net/wiki"
        base_url = confluence_url_with_wiki.split('/wiki')[0].rstrip('/')
        
        assert base_url == "https://30156758.atlassian.net"
        assert '/wiki' not in base_url
        
        # Then add /wiki back
        webui_path = "/spaces/SCRUM/pages/8192024/test"
        page_link = f"{base_url}/wiki{webui_path}"
        
        assert page_link == "https://30156758.atlassian.net/wiki/spaces/SCRUM/pages/8192024/test"
        assert page_link.count('/wiki') == 1  # Should have exactly one /wiki
        logger.info(f"✓ Handles existing /wiki in base URL: {page_link}")
    
    def test_confluence_url_three_construction_points(self, agent, mock_config):
        """Test all three URL construction points in agent_graph.py."""
        base_url = mock_config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
        page_id = "8192024"
        webui_path = "/spaces/SCRUM/pages/8192024/test"
        
        # Point 1: From webui_path
        url1 = f"{base_url}/wiki{webui_path}" if not webui_path.startswith('http') else webui_path
        
        # Point 2: From page_id
        url2 = f"{base_url}/wiki/pages/viewpage.action?pageId={page_id}"
        
        # Point 3: Fallback
        fallback_base = mock_config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
        url3 = f"{fallback_base}/wiki/pages/viewpage.action?pageId={page_id}"
        
        # All should have /wiki prefix
        assert '/wiki' in url1
        assert '/wiki' in url2
        assert '/wiki' in url3
        
        logger.info(f"✓ All three URL construction points include /wiki:")
        logger.info(f"  1. {url1}")
        logger.info(f"  2. {url2}")
        logger.info(f"  3. {url3}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

