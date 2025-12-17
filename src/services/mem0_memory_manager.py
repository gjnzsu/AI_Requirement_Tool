"""
Mem0-based Memory Manager for advanced memory capabilities.

This adapter integrates Mem0's memory system with the existing chatbot architecture.
Mem0 provides:
- Semantic memory search
- Automatic memory summarization
- Multi-type memory (episodic, semantic, factual)
- Graph-based memory relationships
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import json
from pathlib import Path

try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    print("⚠ Mem0 not installed. Install with: pip install mem0ai")

from src.utils.logger import get_logger

logger = get_logger('chatbot.services.mem0_memory')


class Mem0MemoryManager:
    """
    Mem0-based memory manager with advanced memory capabilities.
    
    Features:
    - Semantic memory search
    - Automatic memory summarization
    - Multi-type memory support
    - Graph-based relationships
    """
    
    def __init__(self, 
                 user_id: Optional[str] = None,
                 agent_id: Optional[str] = None,
                 config: Optional[Dict] = None):
        """
        Initialize Mem0 Memory Manager.
        
        Args:
            user_id: User identifier (for user-specific memories)
            agent_id: Agent identifier (for agent-specific memories)
            config: Mem0 configuration dictionary
        """
        if not MEM0_AVAILABLE:
            raise ImportError("Mem0 is not installed. Install with: pip install mem0ai")
        
        # Default configuration
        default_config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "chatbot_memories",
                    "path": str(Path(__file__).parent.parent.parent / "data" / "mem0_vector_store")
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-3.5-turbo"
                }
            }
        }
        
        # Merge with provided config
        if config:
            default_config.update(config)
        
        self.config = default_config
        self.user_id = user_id or "default_user"
        self.agent_id = agent_id or "chatbot_agent"
        
        # Initialize Mem0 Memory
        try:
            self.memory = Memory.from_config(self.config)
            logger.info("✓ Initialized Mem0 Memory Manager")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            raise
    
    def add_memory(self, 
                   messages: List[Dict[str, str]], 
                   metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Add conversation memory to Mem0.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            metadata: Optional metadata dictionary
            
        Returns:
            Memory creation result
        """
        try:
            # Format messages for Mem0
            memory_data = {
                "messages": messages,
                "user_id": self.user_id,
                "agent_id": self.agent_id
            }
            
            if metadata:
                memory_data["metadata"] = metadata
            
            # Add memory
            result = self.memory.add(memory_data)
            logger.info(f"✓ Added memory to Mem0: {len(messages)} messages")
            return result
            
        except Exception as e:
            logger.error(f"Error adding memory to Mem0: {e}")
            raise
    
    def search_memories(self, 
                       query: str, 
                       limit: int = 5,
                       memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search memories using semantic search.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            memory_type: Optional memory type filter ('episodic', 'semantic', 'factual')
            
        Returns:
            List of relevant memories
        """
        try:
            search_params = {
                "query": query,
                "user_id": self.user_id,
                "agent_id": self.agent_id,
                "limit": limit
            }
            
            if memory_type:
                search_params["memory_type"] = memory_type
            
            results = self.memory.search(**search_params)
            logger.debug(f"Found {len(results)} memories for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    def get_all_memories(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all memories for the user/agent.
        
        Args:
            limit: Maximum number of memories to return
            
        Returns:
            List of all memories
        """
        try:
            params = {
                "user_id": self.user_id,
                "agent_id": self.agent_id
            }
            
            if limit:
                params["limit"] = limit
            
            memories = self.memory.get_all(**params)
            return memories
            
        except Exception as e:
            logger.error(f"Error getting all memories: {e}")
            return []
    
    def get_relevant_memories(self, 
                              user_input: str,
                              conversation_history: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """
        Get relevant memories for a user input, combining semantic search with conversation context.
        
        Args:
            user_input: Current user input
            conversation_history: Previous conversation messages
            
        Returns:
            List of relevant memories formatted for LLM context
        """
        try:
            # Search for relevant memories
            memories = self.search_memories(user_input, limit=5)
            
            # Format memories for LLM context
            formatted_memories = []
            for memory in memories:
                formatted_memories.append({
                    "type": memory.get("memory_type", "episodic"),
                    "content": memory.get("memory", ""),
                    "metadata": memory.get("metadata", {}),
                    "relevance_score": memory.get("score", 0.0)
                })
            
            return formatted_memories
            
        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return []
    
    def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing memory.
        
        Args:
            memory_id: Memory identifier
            updates: Dictionary of updates
            
        Returns:
            True if successful
        """
        try:
            self.memory.update(memory_id, updates)
            logger.info(f"✓ Updated memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            True if successful
        """
        try:
            self.memory.delete(memory_id)
            logger.info(f"✓ Deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False
    
    def delete_all_memories(self) -> bool:
        """
        Delete all memories for the user/agent.
        
        Returns:
            True if successful
        """
        try:
            memories = self.get_all_memories()
            for memory in memories:
                memory_id = memory.get("id") or memory.get("memory_id")
                if memory_id:
                    self.delete_memory(memory_id)
            logger.info("✓ Deleted all memories")
            return True
        except Exception as e:
            logger.error(f"Error deleting all memories: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored memories.
        
        Returns:
            Dictionary with memory statistics
        """
        try:
            all_memories = self.get_all_memories()
            return {
                "total_memories": len(all_memories),
                "user_id": self.user_id,
                "agent_id": self.agent_id
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"total_memories": 0}

