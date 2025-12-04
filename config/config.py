"""
Configuration file for Jira Maturity Evaluator Service.

Set these as environment variables or create a .env file in the project root.
The .env file will be automatically loaded if python-dotenv is installed.
"""

import os
from typing import Optional

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use environment variables only


class Config:
    """Configuration class for Jira and LLM settings."""
    
    # Jira Configuration
    JIRA_URL: str = os.getenv('JIRA_URL', 'https://yourcompany.atlassian.net')
    JIRA_EMAIL: str = os.getenv('JIRA_EMAIL', 'your-email@example.com')
    JIRA_API_TOKEN: str = os.getenv('JIRA_API_TOKEN', 'your-api-token')
    JIRA_PROJECT_KEY: str = os.getenv('JIRA_PROJECT_KEY', 'PROJ')
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', 'your-openai-api-key')
    # Default to gpt-3.5-turbo as it's more accessible. Use gpt-4 if you have access.
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Evaluation Settings
    MAX_BACKLOG_ITEMS: int = int(os.getenv('MAX_BACKLOG_ITEMS', '50'))
    
    # Optional: Custom field ID to store maturity score in Jira
    JIRA_MATURITY_SCORE_FIELD: Optional[str] = os.getenv('JIRA_MATURITY_SCORE_FIELD', None)
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is set."""
        required_fields = [
            cls.JIRA_URL,
            cls.JIRA_EMAIL,
            cls.JIRA_API_TOKEN,
            cls.JIRA_PROJECT_KEY,
            cls.OPENAI_API_KEY
        ]
        
        if any(field.startswith('your-') or field == '' for field in required_fields):
            return False
        return True

