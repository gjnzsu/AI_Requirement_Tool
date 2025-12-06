"""
Chat Memory Manager for persistent conversation storage and context management.

This module provides:
- Persistent storage using SQLite database
- Conversation and message management
- Context window management with smart truncation
- Memory summarization for long conversations
- Search and retrieval capabilities
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager


class MemoryManager:
    """
    Manages persistent storage and retrieval of conversation history.
    
    Features:
    - SQLite-based persistent storage
    - Conversation and message management
    - Context window management
    - Memory summarization
    """
    
    def __init__(self, db_path: Optional[str] = None, max_context_messages: int = 50):
        """
        Initialize the memory manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses default location.
            max_context_messages: Maximum number of messages to keep in context window
        """
        # Set default database path
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / 'chatbot_memory.db')
        
        self.db_path = db_path
        self.max_context_messages = max_context_messages
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the SQLite database with required tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT,
                    summary TEXT
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_updated 
                ON conversations(updated_at)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_conversation(self, conversation_id: str, title: str = "New Chat", 
                           metadata: Optional[Dict] = None) -> bool:
        """
        Create a new conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            title: Conversation title
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful
        """
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO conversations 
                (id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, title, now, now, metadata_json))
        
        return True
    
    def add_message(self, conversation_id: str, role: str, content: str,
                   metadata: Optional[Dict] = None) -> int:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation identifier
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata dictionary
            
        Returns:
            Message ID
        """
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (conversation_id, role, content, timestamp, metadata_json))
            
            message_id = cursor.lastrowid
            
            # Update conversation's updated_at timestamp
            cursor.execute("""
                UPDATE conversations 
                SET updated_at = ?
                WHERE id = ?
            """, (timestamp, conversation_id))
        
        return message_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Get a conversation with all its messages.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Dictionary with conversation data and messages, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get conversation
            cursor.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conversation_id,))
            
            conv_row = cursor.fetchone()
            if not conv_row:
                return None
            
            # Get messages
            cursor.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """, (conversation_id,))
            
            message_rows = cursor.fetchall()
            
            # Build conversation dictionary
            conversation = {
                'id': conv_row['id'],
                'title': conv_row['title'],
                'created_at': conv_row['created_at'],
                'updated_at': conv_row['updated_at'],
                'summary': conv_row['summary'],
                'metadata': json.loads(conv_row['metadata']) if conv_row['metadata'] else {},
                'messages': [
                    {
                        'id': msg['id'],
                        'role': msg['role'],
                        'content': msg['content'],
                        'timestamp': msg['timestamp'],
                        'metadata': json.loads(msg['metadata']) if msg['metadata'] else {}
                    }
                    for msg in message_rows
                ]
            }
            
            return conversation
    
    def get_conversation_messages(self, conversation_id: str, 
                                  limit: Optional[int] = None) -> List[Dict]:
        """
        Get messages for a conversation, optionally limited.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return (None for all)
            
        Returns:
            List of message dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, (conversation_id,))
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row['id'],
                    'role': row['role'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                for row in rows
            ]
    
    def get_conversation_context(self, conversation_id: str, 
                                 max_messages: Optional[int] = None) -> List[Dict]:
        """
        Get conversation context for LLM, with smart truncation.
        
        This method returns messages optimized for context window:
        - If conversation is short, returns all messages
        - If conversation is long, returns recent messages + summary of older messages
        
        Args:
            conversation_id: Conversation identifier
            max_messages: Maximum messages to include (uses self.max_context_messages if None)
            
        Returns:
            List of message dictionaries optimized for context
        """
        max_msgs = max_messages or self.max_context_messages
        
        # Get all messages
        all_messages = self.get_conversation_messages(conversation_id)
        
        if len(all_messages) <= max_msgs:
            # Short conversation, return all
            return all_messages
        
        # Long conversation - get summary and recent messages
        conversation = self.get_conversation(conversation_id)
        summary = conversation.get('summary') if conversation else None
        
        # Get recent messages
        recent_messages = all_messages[-max_msgs:]
        
        # If we have a summary, prepend it as a system message
        if summary:
            context = [
                {
                    'role': 'system',
                    'content': f"Previous conversation summary: {summary}",
                    'timestamp': all_messages[0]['timestamp'] if all_messages else datetime.now().isoformat()
                }
            ]
            context.extend(recent_messages)
            return context
        
        # No summary yet, just return recent messages
        return recent_messages
    
    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        """Update conversation title."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET title = ?, updated_at = ?
                WHERE id = ?
            """, (title, datetime.now().isoformat(), conversation_id))
        
        return True
    
    def update_conversation_summary(self, conversation_id: str, summary: str) -> bool:
        """Update conversation summary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET summary = ?, updated_at = ?
                WHERE id = ?
            """, (summary, datetime.now().isoformat(), conversation_id))
        
        return True
    
    def list_conversations(self, limit: Optional[int] = None, 
                          order_by: str = 'updated_at') -> List[Dict]:
        """
        List all conversations.
        
        Args:
            limit: Maximum number of conversations to return
            order_by: Field to order by ('updated_at', 'created_at', 'title')
            
        Returns:
            List of conversation dictionaries (without messages)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = f"""
                SELECT c.*, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id
                ORDER BY c.{order_by} DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row['id'],
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'summary': row['summary'],
                    'message_count': row['message_count'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                for row in rows
            ]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        return True
    
    def delete_all_conversations(self) -> bool:
        """Delete all conversations and messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM conversations")
        
        return True
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search conversations by title or message content.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching conversations
        """
        search_term = f"%{query}%"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT c.*, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.title LIKE ? OR m.content LIKE ?
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (search_term, search_term, limit))
            
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row['id'],
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                    'summary': row['summary'],
                    'message_count': row['message_count'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                for row in rows
            ]
    
    def get_statistics(self) -> Dict:
        """Get memory statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total conversations
            cursor.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cursor.fetchone()[0]
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Average messages per conversation
            avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
            
            return {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'average_messages_per_conversation': round(avg_messages, 2)
            }

