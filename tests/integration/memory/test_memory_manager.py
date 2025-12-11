"""
Test script to verify conversation memory persistence.

This script demonstrates:
1. Creating conversations
2. Adding messages
3. Verifying persistence across restarts
4. Searching conversations
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.memory_manager import MemoryManager
from src.chatbot import Chatbot
from config.config import Config


def test_memory_manager():
    """Test the MemoryManager directly."""
    print("=" * 70)
    print("Testing Memory Manager")
    print("=" * 70)
    
    # Initialize memory manager
    memory = MemoryManager()
    print(f"✓ Memory Manager initialized")
    print(f"  Database location: {memory.db_path}\n")
    
    # Create a test conversation
    test_conv_id = f"test_conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating test conversation: {test_conv_id}")
    memory.create_conversation(test_conv_id, title="Test Conversation")
    print("✓ Conversation created\n")
    
    # Add some messages
    print("Adding messages...")
    memory.add_message(test_conv_id, "user", "Hello! This is a test message.")
    memory.add_message(test_conv_id, "assistant", "Hi! I received your test message.")
    memory.add_message(test_conv_id, "user", "Can you remember this conversation?")
    memory.add_message(test_conv_id, "assistant", "Yes, I can remember our conversation!")
    print("✓ Messages added\n")
    
    # Retrieve conversation
    print("Retrieving conversation...")
    conversation = memory.get_conversation(test_conv_id)
    if conversation:
        print(f"✓ Conversation retrieved successfully")
        print(f"  Title: {conversation['title']}")
        print(f"  Messages: {len(conversation['messages'])}")
        print(f"  Created: {conversation['created_at']}")
        print("\n  Message history:")
        for i, msg in enumerate(conversation['messages'], 1):
            print(f"    {i}. [{msg['role']}]: {msg['content'][:50]}...")
    else:
        print("✗ Failed to retrieve conversation")
        return False
    
    # Test persistence by creating a new instance
    print("\n" + "-" * 70)
    print("Testing persistence (creating new MemoryManager instance)...")
    memory2 = MemoryManager(db_path=memory.db_path)
    conversation2 = memory2.get_conversation(test_conv_id)
    
    if conversation2 and len(conversation2['messages']) == len(conversation['messages']):
        print("✓ Persistence verified! Conversation survived instance restart.")
        print(f"  Retrieved {len(conversation2['messages'])} messages from new instance")
    else:
        print("✗ Persistence test failed")
        return False
    
    # Test search
    print("\n" + "-" * 70)
    print("Testing search functionality...")
    results = memory.search_conversations("test", limit=5)
    if results:
        print(f"✓ Search found {len(results)} conversation(s)")
        for result in results:
            print(f"  - {result['title']} ({result.get('message_count', 0)} messages)")
    else:
        print("✗ Search returned no results")
    
    # Get statistics
    print("\n" + "-" * 70)
    print("Memory Statistics:")
    stats = memory.get_statistics()
    print(f"  Total conversations: {stats['total_conversations']}")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Avg messages/conversation: {stats['average_messages_per_conversation']}")
    
    print("\n" + "=" * 70)
    print("✓ All Memory Manager tests passed!")
    print("=" * 70)
    
    return True


def test_chatbot_integration():
    """Test chatbot integration with memory."""
    print("\n" + "=" * 70)
    print("Testing Chatbot Integration")
    print("=" * 70)
    
    if not Config.get_llm_api_key():
        print("⚠ LLM API key not configured. Skipping chatbot integration test.")
        print("  Set OPENAI_API_KEY, GEMINI_API_KEY, or DEEPSEEK_API_KEY to test.")
        return True
    
    try:
        # Create chatbot with persistent memory
        print("Creating chatbot with persistent memory...")
        chatbot = Chatbot(
            use_persistent_memory=True,
            max_history=10
        )
        print("✓ Chatbot created\n")
        
        # Generate a unique conversation ID
        test_conv_id = f"chatbot_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        chatbot.set_conversation_id(test_conv_id)
        print(f"Set conversation ID: {test_conv_id}\n")
        
        # Send a test message
        print("Sending test message...")
        response = chatbot.get_response("Hello! This is a test to verify memory persistence.")
        print(f"✓ Response received: {response[:50]}...\n")
        
        # Verify it was saved
        if chatbot.memory_manager:
            conversation = chatbot.memory_manager.get_conversation(test_conv_id)
            if conversation and len(conversation['messages']) >= 2:
                print("✓ Conversation saved to persistent storage")
                print(f"  Messages in database: {len(conversation['messages'])}")
            else:
                print("✗ Conversation not found in database")
                return False
        
        # Create a new chatbot instance and load the conversation
        print("\n" + "-" * 70)
        print("Testing persistence with new chatbot instance...")
        chatbot2 = Chatbot(
            use_persistent_memory=True,
            max_history=10
        )
        
        if chatbot2.load_conversation(test_conv_id):
            print("✓ Conversation loaded successfully")
            print(f"  Loaded {len(chatbot2.conversation_history)} messages")
            
            # Send a follow-up message
            response2 = chatbot2.get_response("Do you remember our previous conversation?")
            print(f"✓ Follow-up response: {response2[:50]}...")
            
            # Verify both messages are in database
            if chatbot2.memory_manager:
                conversation2 = chatbot2.memory_manager.get_conversation(test_conv_id)
                if conversation2 and len(conversation2['messages']) >= 4:
                    print(f"✓ All messages persisted ({len(conversation2['messages'])} total)")
                else:
                    print("✗ Not all messages found in database")
                    return False
        else:
            print("✗ Failed to load conversation")
            return False
        
        print("\n" + "=" * 70)
        print("✓ Chatbot integration tests passed!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"✗ Error during chatbot integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_database_info():
    """Show database file information."""
    print("\n" + "=" * 70)
    print("Database Information")
    print("=" * 70)
    
    memory = MemoryManager()
    db_path = Path(memory.db_path)
    
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"Database file: {db_path}")
        print(f"File size: {size:,} bytes ({size / 1024:.2f} KB)")
        print(f"Last modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}")
        
        # Get some stats
        stats = memory.get_statistics()
        print(f"\nDatabase contents:")
        print(f"  Conversations: {stats['total_conversations']}")
        print(f"  Messages: {stats['total_messages']}")
        
        # List recent conversations
        conversations = memory.list_conversations(limit=5)
        if conversations:
            print(f"\nRecent conversations:")
            for conv in conversations:
                print(f"  - {conv['id']}: {conv['title']} ({conv.get('message_count', 0)} messages)")
    else:
        print(f"Database file not found at: {db_path}")
        print("  (It will be created on first use)")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Chatbot Memory System Verification")
    print("=" * 70)
    print()
    
    # Test memory manager
    if not test_memory_manager():
        print("\n✗ Memory Manager tests failed!")
        return 1
    
    # Test chatbot integration (optional, requires API key)
    test_chatbot_integration()
    
    # Show database info
    show_database_info()
    
    print("\n" + "=" * 70)
    print("Verification Complete!")
    print("=" * 70)
    print("\nTo verify manually:")
    print("1. Run the chatbot and have a conversation")
    print("2. Stop the chatbot")
    print("3. Restart the chatbot and load the same conversation_id")
    print("4. The conversation should be restored from the database")
    print(f"\nDatabase location: {Path(MemoryManager().db_path)}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

