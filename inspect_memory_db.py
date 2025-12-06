"""
Inspect the memory database directly.

This script allows you to view conversations and messages stored in the database.
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.memory_manager import MemoryManager


def inspect_database():
    """Inspect the database contents."""
    memory = MemoryManager()
    db_path = Path(memory.db_path)
    
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        print("Create a conversation first by running the chatbot.")
        return
    
    print("=" * 70)
    print("Memory Database Inspector")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Size: {db_path.stat().st_size:,} bytes")
    print()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get conversation count
    cursor.execute("SELECT COUNT(*) FROM conversations")
    conv_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    msg_count = cursor.fetchone()[0]
    
    print(f"Total Conversations: {conv_count}")
    print(f"Total Messages: {msg_count}")
    print()
    
    if conv_count == 0:
        print("No conversations found in database.")
        conn.close()
        return
    
    # List all conversations
    print("=" * 70)
    print("Conversations")
    print("=" * 70)
    cursor.execute("""
        SELECT c.*, COUNT(m.id) as message_count
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        GROUP BY c.id
        ORDER BY c.updated_at DESC
    """)
    
    conversations = cursor.fetchall()
    for i, conv in enumerate(conversations, 1):
        print(f"\n{i}. Conversation ID: {conv['id']}")
        print(f"   Title: {conv['title']}")
        print(f"   Created: {conv['created_at']}")
        print(f"   Updated: {conv['updated_at']}")
        print(f"   Messages: {conv['message_count']}")
        if conv['summary']:
            print(f"   Summary: {conv['summary'][:100]}...")
        if conv['metadata']:
            metadata = json.loads(conv['metadata'])
            if metadata:
                print(f"   Metadata: {metadata}")
    
    # Show detailed view of first conversation
    if conversations:
        print("\n" + "=" * 70)
        print(f"Detailed View: {conversations[0]['id']}")
        print("=" * 70)
        
        conv_id = conversations[0]['id']
        cursor.execute("""
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """, (conv_id,))
        
        messages = cursor.fetchall()
        print(f"\nMessages ({len(messages)} total):\n")
        
        for i, msg in enumerate(messages, 1):
            timestamp = msg['timestamp']
            role = msg['role']
            content = msg['content']
            print(f"{i}. [{role.upper()}] ({timestamp})")
            print(f"   {content[:200]}{'...' if len(content) > 200 else ''}")
            print()
    
    conn.close()


def show_conversation(conversation_id: str):
    """Show details of a specific conversation."""
    memory = MemoryManager()
    conversation = memory.get_conversation(conversation_id)
    
    if not conversation:
        print(f"Conversation '{conversation_id}' not found.")
        return
    
    print("=" * 70)
    print(f"Conversation: {conversation_id}")
    print("=" * 70)
    print(f"Title: {conversation['title']}")
    print(f"Created: {conversation['created_at']}")
    print(f"Updated: {conversation['updated_at']}")
    if conversation.get('summary'):
        print(f"\nSummary:\n{conversation['summary']}")
    print(f"\nMessages ({len(conversation['messages'])} total):\n")
    
    for i, msg in enumerate(conversation['messages'], 1):
        print(f"{i}. [{msg['role'].upper()}] ({msg['timestamp']})")
        print(f"   {msg['content']}")
        print()


def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Show specific conversation
        conversation_id = sys.argv[1]
        show_conversation(conversation_id)
    else:
        # Show overview
        inspect_database()
        
        print("\n" + "=" * 70)
        print("Usage:")
        print("  python inspect_memory_db.py                    # Show overview")
        print("  python inspect_memory_db.py <conversation_id>   # Show specific conversation")
        print("=" * 70)


if __name__ == "__main__":
    main()

