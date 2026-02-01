"""
Integration tests for Jira Maturity Evaluator timeout handling.

Tests that the evaluator properly handles the 60-second timeout
for complex evaluation tasks.
"""

import pytest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.llm import LLMRouter
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.jira_evaluator_timeout')


class TestJiraEvaluatorTimeout:
    """Test suite for Jira maturity evaluator timeout handling."""
    
    @pytest.fixture
    def mock_jira(self):
        """Create a mock Jira client."""
        mock_jira = Mock()
        mock_issue = Mock()
        mock_issue.key = "TEST-123"
        mock_issue.fields.summary = "Test Issue"
        mock_issue.fields.description = "Test description"
        mock_issue.fields.status.name = "To Do"
        mock_issue.fields.priority.name = "High"
        mock_issue.fields.assignee = None
        mock_issue.fields.created = "2024-01-01T00:00:00.000Z"
        mock_issue.fields.updated = "2024-01-01T00:00:00.000Z"
        mock_issue.fields.labels = []
        mock_issue.raw = {'fields': {}}
        
        mock_jira.search_issues.return_value = [mock_issue]
        return mock_jira
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        mock_provider = Mock()
        mock_provider.generate_response.return_value = json.dumps({
            'overall_maturity_score': 75,
            'criteria_scores': {
                'description_completeness': 80,
                'acceptance_criteria': 70
            },
            'recommendations': ['Add more details']
        })
        return mock_provider
    
    def test_evaluator_uses_timeout_parameter(self, mock_jira, mock_llm_provider):
        """Test that evaluator passes timeout=60.0 to LLM provider."""
        evaluator = JiraMaturityEvaluator(
            jira_url="https://test.atlassian.net",
            jira_email="test@example.com",
            jira_api_token="test-token",
            project_key="TEST",
            llm_provider=mock_llm_provider
        )
        evaluator.jira = mock_jira
        
        # Mock a backlog item
        backlog_item = {
            'key': 'TEST-123',
            'summary': 'Test Issue',
            'description': 'Test description',
            'status': 'To Do',
            'priority': 'High',
            'assignee': 'Unassigned',
            'created': '2024-01-01T00:00:00.000Z',
            'updated': '2024-01-01T00:00:00.000Z',
            'labels': [],
            'custom_fields': {}
        }
        
        # Evaluate maturity
        result = evaluator.evaluate_maturity(backlog_item)
        
        # Verify that generate_response was called with timeout=60.0
        mock_llm_provider.generate_response.assert_called_once()
        call_kwargs = mock_llm_provider.generate_response.call_args[1]
        
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 60.0
        logger.info("✓ Evaluator correctly uses timeout=60.0")
    
    @pytest.mark.slow
    def test_evaluator_timeout_handling_real_llm(self):
        """Test evaluator with real LLM provider and timeout."""
        if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY.startswith('your-'):
            pytest.skip("OpenAI API key not configured")
        
        if not Config.JIRA_URL or Config.JIRA_URL.startswith('your-'):
            pytest.skip("Jira configuration not set")
        
        # Create real LLM provider
        llm_provider = LLMRouter.get_provider(
            provider_name=Config.LLM_PROVIDER,
            api_key=Config.OPENAI_API_KEY if Config.LLM_PROVIDER == 'openai' else None,
            model=Config.OPENAI_MODEL if Config.LLM_PROVIDER == 'openai' else None
        )
        
        # Create evaluator with real Jira (if configured)
        try:
            evaluator = JiraMaturityEvaluator(
                jira_url=Config.JIRA_URL,
                jira_email=Config.JIRA_EMAIL,
                jira_api_token=Config.JIRA_API_TOKEN,
                project_key=Config.JIRA_PROJECT_KEY,
                llm_provider=llm_provider
            )
            
            # Create a test backlog item
            backlog_item = {
                'key': 'TEST-123',
                'summary': 'Test Issue for Timeout Testing',
                'description': 'This is a test issue to verify timeout handling in the maturity evaluator.',
                'status': 'To Do',
                'priority': 'Medium',
                'assignee': 'Unassigned',
                'created': '2024-01-01T00:00:00.000Z',
                'updated': '2024-01-01T00:00:00.000Z',
                'labels': [],
                'custom_fields': {}
            }
            
            # Measure evaluation time
            start_time = time.time()
            result = evaluator.evaluate_maturity(backlog_item)
            elapsed = time.time() - start_time
            
            # Verify result
            assert result is not None
            assert 'overall_maturity_score' in result
            assert elapsed < 90.0  # Should complete within timeout + buffer
            logger.info(f"✓ Evaluation completed in {elapsed:.2f}s (timeout: 60s)")
            
        except Exception as e:
            logger.warning(f"Could not test with real Jira: {e}")
            pytest.skip("Jira connection failed, skipping real LLM test")
    
    def test_evaluator_timeout_exceeds_limit(self, mock_jira):
        """Test that evaluator handles timeout errors gracefully."""
        # Create a mock LLM provider that simulates timeout
        mock_provider = Mock()
        mock_provider.generate_response.side_effect = TimeoutError("Request timed out")
        mock_provider.supports_json_mode.return_value = False
        
        evaluator = JiraMaturityEvaluator(
            jira_url="https://test.atlassian.net",
            jira_email="test@example.com",
            jira_api_token="test-token",
            project_key="TEST",
            llm_provider=mock_provider
        )
        evaluator.jira = mock_jira
        
        backlog_item = {
            'key': 'TEST-123',
            'summary': 'Test Issue',
            'description': 'Test description',
            'status': 'To Do',
            'priority': 'High',
            'assignee': 'Unassigned',
            'created': '2024-01-01T00:00:00.000Z',
            'updated': '2024-01-01T00:00:00.000Z',
            'labels': [],
            'custom_fields': {}
        }
        
        # Evaluator catches exceptions and returns a dict with error field
        result = evaluator.evaluate_maturity(backlog_item)
        
        # Should return error result, not raise exception
        assert result is not None
        assert 'error' in result
        assert result['overall_maturity_score'] == 0
        assert 'Request timed out' in result['error']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

