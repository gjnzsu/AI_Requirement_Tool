"""
Gateway Configuration.

Configuration settings for the AI Gateway service.
"""

import os
from typing import Optional, List
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    
    # Try production env first
    production_env = Path('/etc/chatbot/.env')
    if production_env.exists():
        load_dotenv(dotenv_path=production_env, override=False)
    
    # Also try project root .env
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
except ImportError:
    pass
except Exception:
    pass


class GatewayConfig:
    """Configuration class for AI Gateway settings."""
    
    # Gateway Service Settings
    GATEWAY_ENABLED: bool = os.getenv('GATEWAY_ENABLED', 'false').lower() in ('true', '1', 'yes')
    GATEWAY_HOST: str = os.getenv('GATEWAY_HOST', 'localhost')
    GATEWAY_PORT: int = int(os.getenv('GATEWAY_PORT', '8000'))
    
    # Caching Settings
    GATEWAY_CACHE_ENABLED: bool = os.getenv('GATEWAY_CACHE_ENABLED', 'true').lower() in ('true', '1', 'yes')
    GATEWAY_CACHE_TTL: int = int(os.getenv('GATEWAY_CACHE_TTL', '3600'))  # 1 hour default
    GATEWAY_CACHE_BACKEND: str = os.getenv('GATEWAY_CACHE_BACKEND', 'memory')  # 'memory' or 'redis'
    GATEWAY_REDIS_URL: Optional[str] = os.getenv('GATEWAY_REDIS_URL', None)
    
    # Rate Limiting Settings
    GATEWAY_RATE_LIMIT_ENABLED: bool = os.getenv('GATEWAY_RATE_LIMIT_ENABLED', 'true').lower() in ('true', '1', 'yes')
    GATEWAY_RATE_LIMIT_PER_MINUTE: int = int(os.getenv('GATEWAY_RATE_LIMIT_PER_MINUTE', '60'))
    GATEWAY_RATE_LIMIT_PER_HOUR: int = int(os.getenv('GATEWAY_RATE_LIMIT_PER_HOUR', '1000'))
    
    # Fallback Settings
    GATEWAY_FALLBACK_ENABLED: bool = os.getenv('GATEWAY_FALLBACK_ENABLED', 'true').lower() in ('true', '1', 'yes')
    GATEWAY_FALLBACK_PROVIDERS: List[str] = os.getenv(
        'GATEWAY_FALLBACK_PROVIDERS', 
        'openai,gemini,deepseek'
    ).split(',')
    GATEWAY_MAX_RETRIES: int = int(os.getenv('GATEWAY_MAX_RETRIES', '3'))
    GATEWAY_RETRY_BACKOFF_BASE: float = float(os.getenv('GATEWAY_RETRY_BACKOFF_BASE', '2.0'))
    
    # Circuit Breaker Settings
    GATEWAY_CIRCUIT_BREAKER_ENABLED: bool = os.getenv('GATEWAY_CIRCUIT_BREAKER_ENABLED', 'true').lower() in ('true', '1', 'yes')
    GATEWAY_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv('GATEWAY_CIRCUIT_BREAKER_FAILURE_THRESHOLD', '5'))
    GATEWAY_CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = int(os.getenv('GATEWAY_CIRCUIT_BREAKER_RECOVERY_TIMEOUT', '60'))  # seconds
    GATEWAY_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = int(os.getenv('GATEWAY_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS', '3'))
    
    # Routing Settings
    GATEWAY_ROUTING_STRATEGY: str = os.getenv('GATEWAY_ROUTING_STRATEGY', 'auto')  # 'auto', 'cost', 'latency', 'load', 'explicit'
    
    # Metrics Settings
    GATEWAY_METRICS_ENABLED: bool = os.getenv('GATEWAY_METRICS_ENABLED', 'true').lower() in ('true', '1', 'yes')
    
    # Logging Settings
    GATEWAY_LOG_REQUESTS: bool = os.getenv('GATEWAY_LOG_REQUESTS', 'true').lower() in ('true', '1', 'yes')
    GATEWAY_LOG_RESPONSES: bool = os.getenv('GATEWAY_LOG_RESPONSES', 'false').lower() in ('true', '1', 'yes')  # Disabled by default for privacy
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate gateway configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if cls.GATEWAY_CACHE_BACKEND == 'redis' and not cls.GATEWAY_REDIS_URL:
            return False
        if cls.GATEWAY_PORT < 1 or cls.GATEWAY_PORT > 65535:
            return False
        return True

