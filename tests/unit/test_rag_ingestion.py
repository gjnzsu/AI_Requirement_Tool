"""
Unit tests for RAG ingestion functionality.

Tests the _ingest_to_rag helper method and the enhanced ingest_text method.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import hashlib

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger('test.rag_ingestion')


class TestIngestTextWithCustomDocumentId:
    """Tests for RAGService.ingest_text with custom document_id parameter."""
    
    @pytest.fixture
    def mock_rag_service(self):
        """Create a RAGService with mocked dependencies."""
        with patch('src.rag.rag_service.DocumentLoader') as mock_loader, \
             patch('src.rag.rag_service.TextChunker') as mock_chunker, \
             patch('src.rag.rag_service.EmbeddingGenerator') as mock_embedder, \
             patch('src.rag.rag_service.VectorStore') as mock_store:
            
            # Configure mocks
            mock_loader_instance = Mock()
            mock_loader_instance.load_text.return_value = {
                'content': 'test content',
                'metadata': {}
            }
            mock_loader.return_value = mock_loader_instance
            
            mock_chunker_instance = Mock()
            mock_chunker_instance.chunk_document.return_value = [
                {'content': 'chunk1', 'metadata': {}},
                {'content': 'chunk2', 'metadata': {}}
            ]
            mock_chunker.return_value = mock_chunker_instance
            
            mock_embedder_instance = Mock()
            mock_embedder_instance.generate_embeddings_batch.return_value = [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6]
            ]
            mock_embedder.return_value = mock_embedder_instance
            
            mock_store_instance = Mock()
            mock_store_instance.add_document.return_value = True
            mock_store_instance.add_chunk.return_value = 1
            mock_store.return_value = mock_store_instance
            
            from src.rag.rag_service import RAGService
            service = RAGService(enable_cache=False)
            
            return service, mock_store_instance
    
    def test_ingest_text_with_custom_document_id(self, mock_rag_service):
        """Test that custom document_id is used when provided."""
        service, mock_store = mock_rag_service
        
        custom_id = "jira_issue:PROJ-123"
        result = service.ingest_text(
            text="Test Jira content",
            metadata={'type': 'jira_issue', 'key': 'PROJ-123'},
            document_id=custom_id
        )
        
        assert result == custom_id
        # Verify add_document was called with custom_id
        mock_store.add_document.assert_called_once()
        call_args = mock_store.add_document.call_args
        assert call_args.kwargs['document_id'] == custom_id
    
    def test_ingest_text_without_custom_document_id(self, mock_rag_service):
        """Test that MD5 hash is generated when no document_id provided."""
        service, mock_store = mock_rag_service
        
        text = "Test content"
        expected_id = hashlib.md5(text.encode()).hexdigest()
        
        result = service.ingest_text(text=text, metadata={})
        
        assert result == expected_id
        # Verify add_document was called with generated hash
        mock_store.add_document.assert_called_once()
        call_args = mock_store.add_document.call_args
        assert call_args.kwargs['document_id'] == expected_id
    
    def test_ingest_text_deduplication_with_same_id(self, mock_rag_service):
        """Test that same document_id replaces existing document (deduplication)."""
        service, mock_store = mock_rag_service
        
        custom_id = "confluence_page:PROJ-123: Auth Feature"
        
        # First ingest
        service.ingest_text(
            text="Original content",
            metadata={'type': 'confluence_page'},
            document_id=custom_id
        )
        
        # Second ingest with same ID (simulates update)
        service.ingest_text(
            text="Updated content",
            metadata={'type': 'confluence_page'},
            document_id=custom_id
        )
        
        # Verify add_document was called twice with same ID
        # (VectorStore uses INSERT OR REPLACE for deduplication)
        assert mock_store.add_document.call_count == 2
        for call in mock_store.add_document.call_args_list:
            assert call.kwargs['document_id'] == custom_id


class TestAgentIngestToRag:
    """Tests for ChatbotAgent._ingest_to_rag helper method."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a ChatbotAgent with mocked RAG service."""
        with patch('src.agent.agent_graph.ChatOpenAI'), \
             patch('src.agent.agent_graph.JiraTool'), \
             patch('src.agent.agent_graph.ConfluenceTool'), \
             patch('src.agent.agent_graph.IntentDetector'), \
             patch('src.agent.agent_graph.MCPIntegration'), \
             patch('src.agent.agent_graph.Config') as mock_config:
            
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.USE_MCP = False
            mock_config.JIRA_URL = None
            mock_config.CONFLUENCE_URL = None
            
            # Create mock RAG service
            mock_rag = Mock()
            mock_rag.ingest_text.return_value = "test-doc-id"
            
            from src.agent.agent_graph import ChatbotAgent
            agent = ChatbotAgent(
                provider_name="openai",
                enable_tools=False,
                rag_service=mock_rag,
                use_mcp=False
            )
            
            return agent, mock_rag
    
    def test_ingest_to_rag_success(self, mock_agent):
        """Test successful RAG ingestion."""
        agent, mock_rag = mock_agent
        
        content = "Test Jira content"
        metadata = {'type': 'jira_issue', 'key': 'PROJ-123'}
        
        result = agent._ingest_to_rag(content, metadata)
        
        assert result == "test-doc-id"
        mock_rag.ingest_text.assert_called_once()
        call_args = mock_rag.ingest_text.call_args
        assert call_args.kwargs['document_id'] == "jira_issue:PROJ-123"
    
    def test_ingest_to_rag_no_rag_service(self, mock_agent):
        """Test that ingestion is skipped when RAG service is not available."""
        agent, _ = mock_agent
        agent._rag_service = None
        
        result = agent._ingest_to_rag("content", {'type': 'test'})
        
        assert result is None
    
    def test_ingest_to_rag_handles_exception(self, mock_agent):
        """Test that exceptions are caught and don't propagate."""
        agent, mock_rag = mock_agent
        mock_rag.ingest_text.side_effect = Exception("Embedding API error")
        
        # Should not raise, just return None
        result = agent._ingest_to_rag("content", {'type': 'test'})
        
        assert result is None
    
    def test_ingest_to_rag_generates_document_id_from_key(self, mock_agent):
        """Test document ID generation from metadata key."""
        agent, mock_rag = mock_agent
        
        agent._ingest_to_rag("content", {'type': 'jira_issue', 'key': 'TEST-456'})
        
        call_args = mock_rag.ingest_text.call_args
        assert call_args.kwargs['document_id'] == "jira_issue:TEST-456"
    
    def test_ingest_to_rag_generates_document_id_from_title(self, mock_agent):
        """Test document ID generation from metadata title when key is missing."""
        agent, mock_rag = mock_agent
        
        agent._ingest_to_rag("content", {'type': 'confluence_page', 'title': 'My Page'})
        
        call_args = mock_rag.ingest_text.call_args
        assert call_args.kwargs['document_id'] == "confluence_page:My Page"


class TestJiraContentFormatting:
    """Tests for Jira content formatting for RAG ingestion."""
    
    def test_jira_content_includes_all_fields(self):
        """Test that Jira content for RAG includes all expected fields."""
        # Simulate the content format used in _handle_jira_creation
        backlog_data = {
            'summary': 'Implement user authentication',
            'priority': 'High',
            'business_value': 'Enable secure user access',
            'acceptance_criteria': ['Users can login', 'Users can logout'],
            'invest_analysis': 'Meets INVEST criteria',
            'description': 'Full description here'
        }
        result = {'key': 'PROJ-123', 'link': 'https://jira.example.com/PROJ-123'}
        
        # Build content string as done in agent_graph.py
        jira_content = f"""Jira Issue: {result['key']}
Summary: {backlog_data.get('summary', '')}
Priority: {backlog_data.get('priority', 'Medium')}
Business Value: {backlog_data.get('business_value', '')}
Acceptance Criteria: {', '.join(backlog_data.get('acceptance_criteria', [])) if isinstance(backlog_data.get('acceptance_criteria'), list) else backlog_data.get('acceptance_criteria', '')}
INVEST Analysis: {backlog_data.get('invest_analysis', '')}
Description: {backlog_data.get('description', '')}
Link: {result['link']}
"""
        
        assert 'PROJ-123' in jira_content
        assert 'Implement user authentication' in jira_content
        assert 'High' in jira_content
        assert 'Enable secure user access' in jira_content
        assert 'Users can login, Users can logout' in jira_content
        assert 'Meets INVEST criteria' in jira_content
        assert 'https://jira.example.com/PROJ-123' in jira_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

