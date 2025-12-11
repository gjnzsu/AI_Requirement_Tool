"""
Helper functions for test setup and utilities.
"""

import sys
from pathlib import Path


def setup_test_path():
    """Add project root to Python path for tests."""
project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def create_mock_jira_issue(issue_key="TEST-1", summary="Test Issue", description="Test Description"):
    """Create a mock Jira issue dictionary."""
    return {
        'key': issue_key,
        'summary': summary,
        'description': description,
        'status': 'To Do',
        'priority': 'Medium',
        'custom_fields': {}
    }


def create_mock_confluence_page(page_id="12345", title="Test Page", content="Test Content"):
    """Create a mock Confluence page dictionary."""
    return {
        'id': page_id,
        'title': title,
        'content': content,
        'link': f"https://test.atlassian.net/wiki/pages/viewpage.action?pageId={page_id}"
    }

