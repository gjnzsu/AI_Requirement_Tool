"""
Jira Tool for creating and managing Jira issues.
"""

from jira import JIRA
from .base_tool import BaseTool
from config.config import Config
from typing import Dict, Any

class JiraTool(BaseTool):
    """Tool for interacting with Jira."""
    
    def __init__(self):
        self.jira = JIRA(
            server=Config.JIRA_URL,
            basic_auth=(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        )
        self.project_key = Config.JIRA_PROJECT_KEY
    
    def get_name(self) -> str:
        return "jira_tool"
    
    def get_description(self) -> str:
        return "Creates and manages Jira issues (backlog items)"
    
    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute Jira operations.
        
        Args:
            action: The action to perform ('create_issue')
            **kwargs: Arguments for the action
        """
        if action == 'create_issue':
            return self.create_issue(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
            
    def create_issue(self, summary: str, description: str, priority: str = 'Medium', **kwargs) -> Dict[str, Any]:
        """
        Create a new issue in Jira.
        
        Args:
            summary: Issue summary
            description: Issue description (formatted with Biz Value, AC, INVEST)
            priority: Issue priority
            
        Returns:
            Created issue details
        """
        issue_dict = {
            'project': {'key': self.project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Story'},  # Default to Story
            'priority': {'name': priority}
        }
        
        try:
            new_issue = self.jira.create_issue(fields=issue_dict)
            return {
                'success': True,
                'key': new_issue.key,
                'link': f"{Config.JIRA_URL}/browse/{new_issue.key}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

