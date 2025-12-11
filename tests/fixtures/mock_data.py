"""
Mock data generators for tests.
"""


def get_mock_jira_issues(count=3):
    """Generate mock Jira issues."""
    issues = []
    for i in range(1, count + 1):
        issues.append({
            'key': f'TEST-{i}',
            'summary': f'Test Issue {i}',
            'description': f'Description for test issue {i}',
            'status': 'To Do',
            'priority': 'Medium',
            'custom_fields': {}
        })
    return issues


def get_mock_confluence_pages(count=2):
    """Generate mock Confluence pages."""
    pages = []
    for i in range(1, count + 1):
        pages.append({
            'id': str(10000 + i),
            'title': f'Test Page {i}',
            'content': f'Content for test page {i}',
            'link': f'https://test.atlassian.net/wiki/pages/viewpage.action?pageId={10000 + i}'
        })
    return pages


def get_mock_conversation_messages(turn_count=3):
    """Generate mock conversation messages."""
    messages = []
    for i in range(turn_count):
        messages.append({
            'role': 'user',
            'content': f'User message {i + 1}'
        })
        messages.append({
            'role': 'assistant',
            'content': f'Assistant response {i + 1}'
        })
    return messages

