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
    
    # LLM Provider Configuration
    # Supported providers: 'openai', 'gemini', 'deepseek'
    LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'openai')
    
    # Provider-specific API keys
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    DEEPSEEK_API_KEY: str = os.getenv('DEEPSEEK_API_KEY', '')
    
    # Model names (provider-specific)
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-pro')
    DEEPSEEK_MODEL: str = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    # Proxy configuration (for Gemini API access)
    GEMINI_PROXY: Optional[str] = os.getenv('GEMINI_PROXY', None)
    # Alternative: Use standard HTTP_PROXY/HTTPS_PROXY environment variables
    HTTP_PROXY: Optional[str] = os.getenv('HTTP_PROXY', None)
    HTTPS_PROXY: Optional[str] = os.getenv('HTTPS_PROXY', None)
    
    # Evaluation Settings
    MAX_BACKLOG_ITEMS: int = int(os.getenv('MAX_BACKLOG_ITEMS', '50'))
    
    # Optional: Custom field ID to store maturity score in Jira
    JIRA_MATURITY_SCORE_FIELD: Optional[str] = os.getenv('JIRA_MATURITY_SCORE_FIELD', None)
    
    # MCP Settings
    USE_MCP: bool = os.getenv('USE_MCP', 'true').lower() in ('true', '1', 'yes')
    
    # Confluence Configuration
    CONFLUENCE_URL: str = os.getenv('CONFLUENCE_URL', 'https://yourcompany.atlassian.net/wiki')
    CONFLUENCE_SPACE_KEY: str = os.getenv('CONFLUENCE_SPACE_KEY', 'SPACE')
    # Note: Confluence uses the same credentials as Jira (same Atlassian instance)
    
    # Memory Management Configuration
    USE_PERSISTENT_MEMORY: bool = os.getenv('USE_PERSISTENT_MEMORY', 'true').lower() == 'true'
    MEMORY_DB_PATH: Optional[str] = os.getenv('MEMORY_DB_PATH', None)
    MAX_CONTEXT_MESSAGES: int = int(os.getenv('MAX_CONTEXT_MESSAGES', '50'))
    MEMORY_SUMMARY_THRESHOLD: int = int(os.getenv('MEMORY_SUMMARY_THRESHOLD', '30'))
    
    # RAG (Retrieval-Augmented Generation) Configuration
    USE_RAG: bool = os.getenv('USE_RAG', 'true').lower() == 'true'
    RAG_CHUNK_SIZE: int = int(os.getenv('RAG_CHUNK_SIZE', '1000'))
    RAG_CHUNK_OVERLAP: int = int(os.getenv('RAG_CHUNK_OVERLAP', '200'))
    RAG_EMBEDDING_MODEL: str = os.getenv('RAG_EMBEDDING_MODEL', 'text-embedding-ada-002')
    RAG_TOP_K: int = int(os.getenv('RAG_TOP_K', '3'))
    RAG_VECTOR_STORE_PATH: Optional[str] = os.getenv('RAG_VECTOR_STORE_PATH', None)
    RAG_ENABLE_CACHE: bool = os.getenv('RAG_ENABLE_CACHE', 'true').lower() == 'true'
    RAG_CACHE_TTL_HOURS: int = int(os.getenv('RAG_CACHE_TTL_HOURS', '24'))
    
    # MCP Tools Configuration
    ENABLE_MCP_TOOLS: bool = os.getenv('ENABLE_MCP_TOOLS', 'true').lower() == 'true'
    LAZY_LOAD_TOOLS: bool = os.getenv('LAZY_LOAD_TOOLS', 'true').lower() == 'true'
    
    @classmethod
    def get_llm_api_key(cls) -> str:
        """Get the API key for the configured LLM provider."""
        provider = cls.LLM_PROVIDER.lower()
        if provider == 'openai':
            return cls.OPENAI_API_KEY
        elif provider == 'gemini':
            return cls.GEMINI_API_KEY
        elif provider == 'deepseek':
            return cls.DEEPSEEK_API_KEY
        else:
            return ''
    
    @classmethod
    def get_llm_model(cls) -> str:
        """Get the model name for the configured LLM provider."""
        provider = cls.LLM_PROVIDER.lower()
        if provider == 'openai':
            return cls.OPENAI_MODEL
        elif provider == 'gemini':
            return cls.GEMINI_MODEL
        elif provider == 'deepseek':
            return cls.DEEPSEEK_MODEL
        else:
            return ''
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is set."""
        # Validate Jira configuration
        jira_fields = [
            cls.JIRA_URL,
            cls.JIRA_EMAIL,
            cls.JIRA_API_TOKEN,
            cls.JIRA_PROJECT_KEY
        ]
        
        if any(field.startswith('your-') or field == '' for field in jira_fields):
            return False
        
        # Validate LLM configuration
        api_key = cls.get_llm_api_key()
        if not api_key or api_key.startswith('your-'):
            return False
        
        return True

