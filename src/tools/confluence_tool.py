"""
Confluence Tool for creating and managing Confluence pages.
"""

import requests
from requests.auth import HTTPBasicAuth
from .base_tool import BaseTool
from config.config import Config
from typing import Dict, Any, Optional

class ConfluenceTool(BaseTool):
    """Tool for interacting with Confluence."""
    
    def __init__(self):
        self.confluence_url = Config.CONFLUENCE_URL
        self.space_key = Config.CONFLUENCE_SPACE_KEY
        self.auth = HTTPBasicAuth(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        
        # Validate configuration
        if not self.confluence_url or self.confluence_url.startswith('https://yourcompany'):
            raise ValueError(
                "CONFLUENCE_URL is not configured. "
                "Please set CONFLUENCE_URL in your .env file or environment variables."
            )
        
        if not self.space_key or self.space_key == 'SPACE':
            raise ValueError(
                "CONFLUENCE_SPACE_KEY is not configured. "
                "Please set CONFLUENCE_SPACE_KEY in your .env file or environment variables."
            )
        
        self.base_url = f"{self.confluence_url}/rest/api/content"
    
    def get_name(self) -> str:
        return "confluence_tool"
    
    def get_description(self) -> str:
        return "Creates and manages Confluence pages for requirements documentation"
    
    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute Confluence operations.
        
        Args:
            action: The action to perform ('create_page')
            **kwargs: Arguments for the action
        """
        if action == 'create_page':
            return self.create_page(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def create_page(self, title: str, content: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new page in Confluence.
        
        Args:
            title: Page title
            content: Page content in Confluence Storage Format (HTML)
            parent_id: Optional parent page ID
            
        Returns:
            Created page details
        """
        # Convert HTML to Confluence Storage Format
        confluence_content = self._html_to_confluence_storage(content)
        
        page_data = {
            "type": "page",
            "title": title,
            "space": {"key": self.space_key},
            "body": {
                "storage": {
                    "value": confluence_content,
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            page_data["ancestors"] = [{"id": parent_id}]
        
        try:
            response = requests.post(
                self.base_url,
                json=page_data,
                auth=self.auth,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                page = response.json()
                page_link = f"{self.confluence_url}/pages/viewpage.action?pageId={page['id']}"
                return {
                    'success': True,
                    'id': page['id'],
                    'title': page['title'],
                    'link': page_link
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _html_to_confluence_storage(self, html_content: str) -> str:
        """
        Convert HTML content to Confluence Storage Format.
        Basic conversion - can be enhanced for more complex formatting.
        """
        # Confluence Storage Format uses a specific XML-like format
        # For simplicity, we'll use basic HTML that Confluence can understand
        # In production, you might want to use a library like atlassian-python-api
        
        # Basic conversion: wrap in <p> tags if not already wrapped
        if not html_content.strip().startswith('<'):
            html_content = f"<p>{html_content}</p>"
        
        # Replace newlines with <br/> for better formatting
        html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br/>')
        
        return html_content

