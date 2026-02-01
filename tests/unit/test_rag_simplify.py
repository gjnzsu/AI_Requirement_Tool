"""
Unit tests for RAG ingestion optimization (_simplify_for_rag method).

Tests that the _simplify_for_rag method correctly reduces content size
for efficient RAG ingestion while preserving key information.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.agent_graph import ChatbotAgent
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.rag_simplify')


class TestRAGSimplify:
    """Test suite for _simplify_for_rag method."""
    
    @pytest.fixture
    def agent(self):
        """Create a minimal agent instance for testing."""
        # Mock Config properly with string values
        with patch('src.agent.agent_graph.Config') as mock_config:
            mock_config.LLM_PROVIDER = 'openai'
            mock_config.OPENAI_MODEL = 'gpt-3.5-turbo'
            mock_config.OPENAI_API_KEY = 'test-key'
            mock_config.USE_MCP = False
            mock_config.USE_RAG = True
            mock_config.USE_PERSISTENT_MEMORY = False
            
            # Mock other dependencies - patch where they're imported, not where they're used
            with patch('src.llm.LLMRouter'), \
                 patch('src.rag.RAGService'), \
                 patch('src.services.memory_manager.MemoryManager'), \
                 patch('src.mcp.mcp_integration.MCPIntegration'):
                
                agent = ChatbotAgent(
                    provider_name='openai',
                    enable_tools=False,
                    use_mcp=False
                )
                return agent
    
    def test_simplify_basic_content(self, agent):
        """Test basic content simplification."""
        issue_key = "TEST-123"
        backlog_data = {
            'summary': 'Test Issue',
            'priority': 'High',
            'business_value': 'Important feature',
            'acceptance_criteria': ['AC1: First criteria', 'AC2: Second criteria']
        }
        evaluation = {
            'overall_maturity_score': 75
        }
        confluence_link = "https://test.atlassian.net/wiki/pages/viewpage.action?pageId=123"
        
        simplified = agent._simplify_for_rag(
            issue_key, backlog_data, evaluation, confluence_link
        )
        
        # Verify key information is present
        assert issue_key in simplified
        assert backlog_data['summary'] in simplified
        assert confluence_link in simplified
        assert 'Priority: High' in simplified
        assert 'Maturity Score: 75/100' in simplified
        
        # Verify content is significantly reduced
        assert len(simplified) < 1000  # Target: <1000 chars
    
    def test_simplify_truncates_long_business_value(self, agent):
        """Test that long business value is truncated."""
        issue_key = "TEST-123"
        backlog_data = {
            'summary': 'Test Issue',
            'priority': 'Medium',
            'business_value': 'A' * 300,  # 300 character business value
            'acceptance_criteria': []
        }
        evaluation = {'overall_maturity_score': 50}
        confluence_link = "https://test.atlassian.net/wiki/pages/viewpage.action?pageId=123"
        
        simplified = agent._simplify_for_rag(
            issue_key, backlog_data, evaluation, confluence_link
        )
        
        # Business value should be truncated to 150 chars + "..."
        assert 'Business Value:' in simplified
        # Extract the business value part (after "Business Value: " prefix)
        bv_line = simplified.split('Business Value:')[1].split('\n')[0].strip()
        # Should be truncated to 150 chars + "..." = 153 chars max
        assert len(bv_line) <= 153
        # Should end with "..." if truncated
        if len(backlog_data['business_value']) > 150:
            assert bv_line.endswith('...')
    
    def test_simplify_handles_long_acceptance_criteria(self, agent):
        """Test that long acceptance criteria are handled."""
        issue_key = "TEST-123"
        backlog_data = {
            'summary': 'Test Issue',
            'priority': 'Low',
            'business_value': '',
            'acceptance_criteria': [
                'A' * 200,  # Very long first criteria
                'Second criteria',
                'Third criteria'
            ]
        }
        evaluation = {'overall_maturity_score': 60}
        confluence_link = "https://test.atlassian.net/wiki/pages/viewpage.action?pageId=123"
        
        simplified = agent._simplify_for_rag(
            issue_key, backlog_data, evaluation, confluence_link
        )
        
        # Should mention count of acceptance criteria
        assert 'Acceptance Criteria: 3 items' in simplified
        # First criteria should be truncated to 80 chars + "..."
        assert len(simplified.split('  - ')[1].split('\n')[0]) <= 83  # 80 + "..."
    
    def test_simplify_handles_missing_fields(self, agent):
        """Test that missing fields are handled gracefully."""
        issue_key = "TEST-123"
        backlog_data = {
            'summary': 'Test Issue'
            # Missing priority, business_value, acceptance_criteria
        }
        evaluation = {}
        confluence_link = "https://test.atlassian.net/wiki/pages/viewpage.action?pageId=123"
        
        # Should not raise exception
        simplified = agent._simplify_for_rag(
            issue_key, backlog_data, evaluation, confluence_link
        )
        
        assert issue_key in simplified
        assert backlog_data['summary'] in simplified
        assert confluence_link in simplified
    
    def test_simplify_content_size_reduction(self, agent):
        """Test that content size is significantly reduced."""
        issue_key = "TEST-123"
        backlog_data = {
            'summary': 'Test Issue with Long Summary',
            'priority': 'High',
            'business_value': 'A' * 500,  # 500 chars
            'acceptance_criteria': ['B' * 200] * 10  # 10 criteria, 200 chars each
        }
        evaluation = {
            'overall_maturity_score': 80,
            'criteria_scores': {
                'description_completeness': 85,
                'acceptance_criteria': 75
            },
            'recommendations': ['Recommendation 1', 'Recommendation 2']
        }
        confluence_link = "https://test.atlassian.net/wiki/pages/viewpage.action?pageId=123"
        
        simplified = agent._simplify_for_rag(
            issue_key, backlog_data, evaluation, confluence_link
        )
        
        # Original content would be ~4000+ chars (with HTML, full evaluation, etc.)
        # Simplified should be <1000 chars
        assert len(simplified) < 1000
        logger.info(f"Content reduced from ~4000+ chars to {len(simplified)} chars")
    
    def test_simplify_preserves_searchable_keywords(self, agent):
        """Test that searchable keywords are preserved."""
        issue_key = "SCRUM-210"
        backlog_data = {
            'summary': 'Performance tuning on Confluence data sizing',
            'priority': 'High',
            'business_value': 'Improve RAG ingestion performance',
            'acceptance_criteria': ['Reduce content size', 'Maintain searchability']
        }
        evaluation = {'overall_maturity_score': 85}
        confluence_link = "https://test.atlassian.net/wiki/pages/viewpage.action?pageId=123"
        
        simplified = agent._simplify_for_rag(
            issue_key, backlog_data, evaluation, confluence_link
        )
        
        # Key searchable terms should be present
        assert 'Performance' in simplified or 'performance' in simplified
        assert 'Confluence' in simplified or 'confluence' in simplified
        assert 'RAG' in simplified or 'rag' in simplified
        assert issue_key in simplified


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

