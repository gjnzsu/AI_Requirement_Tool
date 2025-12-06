"""
Base class for chatbot tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the tool."""
        pass
        
    @abstractmethod
    def get_description(self) -> str:
        """Get the description of what the tool does."""
        pass
        
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with provided arguments."""
        pass

