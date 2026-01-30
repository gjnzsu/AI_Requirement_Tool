"""
Integration tests for RAG knowledge capture from Jira and Confluence.

Tests the automatic ingestion of created Jira issues and Confluence pages
into the RAG knowledge base for future queries.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger

logger = get_logger('test.rag_knowledge_capture')


@pytest.fixture
def temp_vector_store():
    """Create a temporary vector store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test_vectors.db')
        yield db_path


@pytest.fixture
def rag_service(temp_vector_store):
    """Create a RAGService with mocked embedding generator."""
    with patch('src.rag.rag_service.EmbeddingGenerator') as mock_embedder:
        # Mock embedding generator to avoid API calls
        mock_embedder_instance = Mock()
        mock_embedder_instance.generate_embedding.return_value = [0.1] * 1536
        mock_embedder_instance.generate_embeddings_batch.return_value = [[0.1] * 1536]
        mock_embedder.return_value = mock_embedder_instance
        
        from src.rag.rag_service import RAGService
        service = RAGService(
            vector_store_path=temp_vector_store,
            enable_cache=False
        )
        yield service


class TestRAGKnowledgeCaptureIntegration:
    """Integration tests for RAG knowledge capture."""
    
    def test_ingest_jira_issue_content(self, rag_service):
        """Test ingesting a Jira issue into RAG knowledge base."""
        jira_content = """Jira Issue: PROJ-123
Summary: Implement user authentication
Priority: High
Business Value: Enable secure user access to the platform
Acceptance Criteria: Users can login with email/password, Users can logout, Sessions expire after 24 hours
INVEST Analysis: Independent, Negotiable, Valuable, Estimable, Small, Testable
Description: Implement a complete authentication system with JWT tokens
Link: https://jira.example.com/browse/PROJ-123
Created: 2026-01-29T10:30:00
"""
        
        metadata = {
            'type': 'jira_issue',
            'key': 'PROJ-123',
            'title': 'Implement user authentication',
            'priority': 'High',
            'link': 'https://jira.example.com/browse/PROJ-123',
            'created_at': '2026-01-29T10:30:00'
        }
        
        # Ingest with custom document ID
        doc_id = rag_service.ingest_text(
            jira_content, 
            metadata, 
            document_id='jira_issue:PROJ-123'
        )
        
        assert doc_id == 'jira_issue:PROJ-123'
        
        # Verify document was stored
        stats = rag_service.get_statistics()
        assert stats['total_documents'] >= 1
        assert stats['total_chunks'] >= 1
        
        # Verify document can be listed
        docs = rag_service.list_documents()
        assert any(d['id'] == 'jira_issue:PROJ-123' for d in docs)
    
    def test_ingest_confluence_page_content(self, rag_service):
        """Test ingesting a Confluence page into RAG knowledge base."""
        confluence_content = """PROJ-123: Implement user authentication

## Business Value
Enable secure user access to the platform

## Acceptance Criteria
- Users can login with email/password
- Users can logout
- Sessions expire after 24 hours

## Technical Details
Implement JWT-based authentication with refresh tokens.

## Related Jira Issue
https://jira.example.com/browse/PROJ-123
"""
        
        metadata = {
            'type': 'confluence_page',
            'title': 'PROJ-123: Implement user authentication',
            'related_jira': 'PROJ-123',
            'link': 'https://confluence.example.com/pages/123',
            'page_id': '123',
            'created_at': '2026-01-29T10:35:00'
        }
        
        doc_id = rag_service.ingest_text(
            confluence_content,
            metadata,
            document_id='confluence_page:PROJ-123: Implement user authentication'
        )
        
        assert 'confluence_page' in doc_id
        
        # Verify document was stored
        stats = rag_service.get_statistics()
        assert stats['total_documents'] >= 1
    
    def test_deduplication_on_reingest(self, rag_service):
        """Test that re-ingesting with same ID updates rather than duplicates."""
        original_content = "Original Jira content"
        updated_content = "Updated Jira content with more details"
        
        metadata = {
            'type': 'jira_issue',
            'key': 'TEST-001'
        }
        doc_id = 'jira_issue:TEST-001'
        
        # First ingest
        rag_service.ingest_text(original_content, metadata, document_id=doc_id)
        
        initial_stats = rag_service.get_statistics()
        initial_doc_count = initial_stats['total_documents']
        
        # Re-ingest with same ID (simulating update)
        rag_service.ingest_text(updated_content, metadata, document_id=doc_id)
        
        # Document count should remain the same (not increase)
        final_stats = rag_service.get_statistics()
        assert final_stats['total_documents'] == initial_doc_count
    
    def test_multiple_jira_issues_stored_separately(self, rag_service):
        """Test that different Jira issues are stored as separate documents."""
        issues = [
            ('PROJ-001', 'First issue content'),
            ('PROJ-002', 'Second issue content'),
            ('PROJ-003', 'Third issue content'),
        ]
        
        for key, content in issues:
            rag_service.ingest_text(
                content,
                {'type': 'jira_issue', 'key': key},
                document_id=f'jira_issue:{key}'
            )
        
        # All three should be stored
        stats = rag_service.get_statistics()
        assert stats['total_documents'] >= 3
        
        # Verify each can be found
        docs = rag_service.list_documents()
        doc_ids = [d['id'] for d in docs]
        for key, _ in issues:
            assert f'jira_issue:{key}' in doc_ids
    
    def test_jira_and_confluence_linked_by_key(self, rag_service):
        """Test that Jira issue and related Confluence page can both be ingested."""
        jira_key = 'FEATURE-100'
        
        # Ingest Jira issue
        rag_service.ingest_text(
            f"Jira Issue: {jira_key}\nSummary: New feature",
            {'type': 'jira_issue', 'key': jira_key},
            document_id=f'jira_issue:{jira_key}'
        )
        
        # Ingest related Confluence page
        rag_service.ingest_text(
            f"Confluence page for {jira_key}\nDetailed documentation",
            {'type': 'confluence_page', 'related_jira': jira_key, 'title': f'{jira_key}: New feature'},
            document_id=f'confluence_page:{jira_key}: New feature'
        )
        
        # Both should be stored
        docs = rag_service.list_documents()
        doc_ids = [d['id'] for d in docs]
        
        assert f'jira_issue:{jira_key}' in doc_ids
        assert any('confluence_page' in did and jira_key in did for did in doc_ids)


class TestDirectDocumentLookup:
    """Tests for direct document lookup by Jira key."""
    
    def test_direct_lookup_by_jira_key(self, rag_service):
        """Test that documents can be retrieved directly by Jira key."""
        jira_key = 'LOOKUP-001'
        jira_content = f"Jira Issue: {jira_key}\nSummary: Test direct lookup feature"
        
        # Ingest with standard document ID format
        rag_service.ingest_text(
            jira_content,
            {'type': 'jira_issue', 'key': jira_key},
            document_id=f'jira_issue:{jira_key}'
        )
        
        # Direct lookup should work
        doc = rag_service.vector_store.get_document(f'jira_issue:{jira_key}')
        
        assert doc is not None
        assert jira_key in doc['content']
        assert doc['id'] == f'jira_issue:{jira_key}'
    
    def test_direct_lookup_returns_none_for_missing(self, rag_service):
        """Test that direct lookup returns None for non-existent documents."""
        doc = rag_service.vector_store.get_document('jira_issue:NONEXISTENT-999')
        assert doc is None
    
    def test_direct_lookup_with_confluence_page(self, rag_service):
        """Test direct lookup for Confluence pages related to a Jira key."""
        jira_key = 'LOOKUP-002'
        confluence_content = f"Confluence page for {jira_key}\nDetailed documentation here."
        
        rag_service.ingest_text(
            confluence_content,
            {'type': 'confluence_page', 'related_jira': jira_key},
            document_id=f'confluence_page:{jira_key}: Test Page'
        )
        
        # List documents and find by pattern
        docs = rag_service.vector_store.list_documents()
        matching_docs = [d for d in docs if 'confluence_page' in d['id'] and jira_key in d['id']]
        
        assert len(matching_docs) >= 1


@pytest.mark.slow
class TestRAGQueryAfterIngestion:
    """Tests for querying RAG after knowledge capture."""
    
    def test_retrieve_ingested_jira_content(self, rag_service):
        """Test that ingested Jira content can be retrieved by query."""
        # Ingest a Jira issue
        jira_content = """Jira Issue: AUTH-001
Summary: Implement OAuth2 authentication
Description: Add support for OAuth2 with Google and GitHub providers
Acceptance Criteria: Users can login via Google, Users can login via GitHub
"""
        
        rag_service.ingest_text(
            jira_content,
            {'type': 'jira_issue', 'key': 'AUTH-001'},
            document_id='jira_issue:AUTH-001'
        )
        
        # Query for OAuth2
        results = rag_service.retrieve("OAuth2 authentication", top_k=3)
        
        # Should find the ingested content
        assert len(results) > 0
        assert any('OAuth2' in r['content'] for r in results)
    
    def test_get_context_returns_formatted_results(self, rag_service):
        """Test that get_context returns properly formatted context."""
        # Ingest test content
        rag_service.ingest_text(
            "Feature: Dark mode support\nDescription: Add dark theme to UI",
            {'type': 'jira_issue', 'key': 'UI-001', 'title': 'Dark mode'},
            document_id='jira_issue:UI-001'
        )
        
        context = rag_service.get_context("dark mode theme", top_k=2)
        
        # Context should be a formatted string
        assert isinstance(context, str)
        if context:  # May be empty if embedding similarity is low
            assert 'Relevant context' in context or 'dark' in context.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

