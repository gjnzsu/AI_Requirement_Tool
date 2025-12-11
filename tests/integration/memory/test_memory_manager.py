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
from src.utils.logger import get_logger

logger = get_logger('test.memory_manager')


def test_memory_manager():

    """Test the MemoryManager directly."""
    logger.info("=" * 70)
    logger.info("Testing Memory Manager")
    logger.info("=" * 70)
    
    # Initialize memory manager
    memory = MemoryManager()
    logger.info(f"✓ Memory Manager initialized")
    logger.info(f"  Database location: {memory.db_path}\n")
    
    # Create a test conversation
    test_conv_id = f"test_conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"Creating test conversation: {test_conv_id}")
    memory.create_conversation(test_conv_id, title="Test Conversation")
    logger.info("✓ Conversation created\n")
    
    # Add some messages
    logger.info("Adding messages...")
    memory.add_message(test_conv_id, "user", "Hello! This is a test message.")
    memory.add_message(test_conv_id, "assistant", "Hi! I received your test message.")
    memory.add_message(test_conv_id, "user", "Can you remember this conversation?")
    memory.add_message(test_conv_id, "assistant", "Yes, I can remember our conversation!")
    logger.info("✓ Messages added\n")
    
    # Retrieve conversation
    logger.info("Retrieving conversation...")
    conversation = memory.get_conversation(test_conv_id)
    if conversation:
        logger.info(f"✓ Conversation retrieved successfully")
        logger.info(f"  Title: {conversation['title']}")
        logger.info(f"  Messages: {len(conversation['messages'])}")
        logger.info(f"  Created: {conversation['created_at']}")
        logger.info("\n  Message history:")
        for i, msg in enumerate(conversation['messages'], 1):
            logger.info(f"    {i}. [{msg['role']}]: {msg['content'][:50]}...")
    else:
        logger.error("✗ Failed to retrieve conversation")
        return False
    
    # Test persistence by creating a new instance
    logger.info("\n" + "-" * 70)
    logger.info("Testing persistence (creating new MemoryManager instance)...")
    memory2 = MemoryManager(db_path=memory.db_path)
    conversation2 = memory2.get_conversation(test_conv_id)
    
    if conversation2 and len(conversation2['messages']) == len(conversation['messages']):
        logger.info("✓ Persistence verified! Conversation survived instance restart.")
        logger.info(f"  Retrieved {len(conversation2['messages'])} messages from new instance")
    else:
        logger.error("✗ Persistence test failed")
        return False
    
    # Test search
    logger.info("\n" + "-" * 70)
    logger.info("Testing search functionality...")
    results = memory.search_conversations("test", limit=5)
    if results:
        logger.info(f"✓ Search found {len(results)} conversation(s)")
        for result in results:
            logger.info(f"  - {result['title']} ({result.get('message_count', 0)} messages)")
    else:
        logger.error("✗ Search returned no results")
    
    # Get statistics
    logger.info("\n" + "-" * 70)
    logger.info("Memory Statistics:")
    stats = memory.get_statistics()
    logger.info(f"  Total conversations: {stats['total_conversations']}")
    logger.info(f"  Total messages: {stats['total_messages']}")
    logger.info(f"  Avg messages/conversation: {stats['average_messages_per_conversation']}")
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ All Memory Manager tests passed!")
    logger.info("=" * 70)
    
    return True


def test_chatbot_integration():
    """Test chatbot integration with memory."""
    logger.info("\n" + "=" * 70)
    logger.info("Testing Chatbot Integration")
    logger.info("=" * 70)
    
    if not Config.get_llm_api_key():
        logger.warning("⚠ LLM API key not configured. Skipping chatbot integration test.")
        logger.info("  Set OPENAI_API_KEY, GEMINI_API_KEY, or DEEPSEEK_API_KEY to test.")
        return True
    
    try:
        # Create chatbot with persistent memory
        logger.info("Creating chatbot with persistent memory...")
        chatbot = Chatbot(
            use_persistent_memory=True,
            max_history=10
        )
        logger.info("✓ Chatbot created\n")
        
        # Generate a unique conversation ID
        test_conv_id = f"chatbot_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        chatbot.set_conversation_id(test_conv_id)
        logger.info(f"Set conversation ID: {test_conv_id}\n")
        
        # Send a test message
        logger.info("Sending test message...")
        response = chatbot.get_response("Hello! This is a test to verify memory persistence.")
        logger.info(f"✓ Response received: {response[:50]}...\n")
        
        # Verify it was saved
        if chatbot.memory_manager:
            conversation = chatbot.memory_manager.get_conversation(test_conv_id)
            if conversation and len(conversation['messages']) >= 2:
                logger.info("✓ Conversation saved to persistent storage")
                logger.info(f"  Messages in database: {len(conversation['messages'])}")
            else:
                logger.error("✗ Conversation not found in database")
                return False
        
        # Create a new chatbot instance and load the conversation
        logger.info("\n" + "-" * 70)
        logger.info("Testing persistence with new chatbot instance...")
        chatbot2 = Chatbot(
            use_persistent_memory=True,
            max_history=10
        )
        
        if chatbot2.load_conversation(test_conv_id):
            logger.info("✓ Conversation loaded successfully")
            logger.info(f"  Loaded {len(chatbot2.conversation_history)} messages")
            
            # Send a follow-up message
            response2 = chatbot2.get_response("Do you remember our previous conversation?")
            logger.info(f"✓ Follow-up response: {response2[:50]}...")
            
            # Verify both messages are in database
            if chatbot2.memory_manager:
                conversation2 = chatbot2.memory_manager.get_conversation(test_conv_id)
                if conversation2 and len(conversation2['messages']) >= 4:
                    logger.info(f"✓ All messages persisted ({len(conversation2['messages'])} total)")
                else:
                    logger.error("✗ Not all messages found in database")
                    return False
        else:
            logger.error("✗ Failed to load conversation")
            return False
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ Chatbot integration tests passed!")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error during chatbot integration test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def show_database_info():
    """Show database file information."""
    logger.info("\n" + "=" * 70)
    logger.info("Database Information")
    logger.info("=" * 70)
    
    memory = MemoryManager()
    db_path = Path(memory.db_path)
    
    if db_path.exists():
        size = db_path.stat().st_size
        logger.info(f"Database file: {db_path}")
        logger.info(f"File size: {size:,} bytes ({size / 1024:.2f} KB)")
        logger.info(f"Last modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}")
        
        # Get some stats
        stats = memory.get_statistics()
        logger.info(f"\nDatabase contents:")
        logger.info(f"  Conversations: {stats['total_conversations']}")
        logger.info(f"  Messages: {stats['total_messages']}")
        
        # List recent conversations
        conversations = memory.list_conversations(limit=5)
        if conversations:
            logger.info(f"\nRecent conversations:")
            for conv in conversations:
                logger.info(f"  - {conv['id']}: {conv['title']} ({conv.get('message_count', 0)} messages)")
    else:
        logger.info(f"Database file not found at: {db_path}")
        logger.info("  (It will be created on first use)")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 70)
    logger.info("Chatbot Memory System Verification")
    logger.info("=" * 70)
    logger.info("")
    
    # Test memory manager
    if not test_memory_manager():
        logger.error("\n✗ Memory Manager tests failed!")
        return 1
    
    # Test chatbot integration (optional, requires API key)
    test_chatbot_integration()
    
    # Show database info
    show_database_info()
    
    logger.info("\n" + "=" * 70)
    logger.info("Verification Complete!")
    logger.info("=" * 70)
    logger.info("\nTo verify manually:")
    logger.info("1. Run the chatbot and have a conversation")
    logger.info("2. Stop the chatbot")
    logger.info("3. Restart the chatbot and load the same conversation_id")
    logger.info("4. The conversation should be restored from the database")
    logger.info(f"\nDatabase location: {Path(MemoryManager().db_path)}")
    logger.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

