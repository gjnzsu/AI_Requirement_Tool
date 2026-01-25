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
    from pathlib import Path
    
    # In production, try to load from /etc/chatbot/.env first (systemd service uses this)
    production_env = Path('/etc/chatbot/.env')
    if production_env.exists():
        load_dotenv(dotenv_path=production_env, override=False)
    
    # Also try to load .env from project root (for local development)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        # Prefer real environment variables over .env (standard behavior for deployments/tests)
        load_dotenv(dotenv_path=env_path, override=False)
except ImportError:
    pass  # python-dotenv not installed, use environment variables only
except Exception:
    # If .env file doesn't exist or other error, continue with environment variables
    pass


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
    
    # Mem0 Advanced Memory Configuration
    MEM0_ENABLED: bool = os.getenv('MEM0_ENABLED', 'false').lower() == 'true'
    MEM0_USER_ID: Optional[str] = os.getenv('MEM0_USER_ID', None)
    MEM0_AGENT_ID: Optional[str] = os.getenv('MEM0_AGENT_ID', 'chatbot_agent')
    MEM0_VECTOR_STORE_PATH: Optional[str] = os.getenv('MEM0_VECTOR_STORE_PATH', None)
    MEM0_VECTOR_STORE_PROVIDER: str = os.getenv('MEM0_VECTOR_STORE_PROVIDER', 'chroma')
    MEM0_LLM_MODEL: str = os.getenv('MEM0_LLM_MODEL', 'gpt-3.5-turbo')
    MEM0_LLM_PROVIDER: str = os.getenv('MEM0_LLM_PROVIDER', 'openai')
    
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
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    ENABLE_DEBUG_LOGGING: bool = os.getenv('ENABLE_DEBUG_LOGGING', 'false').lower() in ('true', '1', 'yes')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE', None)  # Optional log file path
    
    # Authentication Configuration
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
    AUTH_DB_PATH: Optional[str] = os.getenv('AUTH_DB_PATH', None)  # Path to auth database, None uses default
    
    # Coze Platform Configuration
    COZE_ENABLED: bool = os.getenv('COZE_ENABLED', 'false').lower() in ('true', '1', 'yes')
    COZE_API_TOKEN: str = os.getenv('COZE_API_TOKEN', '')
    COZE_BOT_ID: str = os.getenv('COZE_BOT_ID', '')
    COZE_API_BASE_URL: str = os.getenv('COZE_API_BASE_URL', 'https://api.coze.com')
    COZE_API_TIMEOUT: int = int(os.getenv('COZE_API_TIMEOUT', '300'))  # Timeout in seconds (default: 300s = 5 minutes)
    
    # Intent Detection Configuration
    INTENT_USE_LLM: bool = os.getenv('INTENT_USE_LLM', 'true').lower() in ('true', '1', 'yes')
    INTENT_LLM_TEMPERATURE: float = float(os.getenv('INTENT_LLM_TEMPERATURE', '0.1'))
    INTENT_CONFIDENCE_THRESHOLD: float = float(os.getenv('INTENT_CONFIDENCE_THRESHOLD', '0.7'))
    INTENT_LLM_TIMEOUT: float = float(os.getenv('INTENT_LLM_TIMEOUT', '5.0'))
    
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

