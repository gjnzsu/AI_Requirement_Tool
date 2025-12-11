"""
Test script to verify conversations persist across service restarts.

This simulates what happens when you restart the Flask server.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.memory_manager import MemoryManager
from src.chatbot import Chatbot
from config.config import Config
from src.utils.logger import get_logger

logger = get_logger('test.memory.persistence')

def simulate_restart_test():
    """Simulate a service restart to verify persistence."""
    logger.info("=" * 70)
    logger.info("Testing Conversation Persistence Across Restarts")
    logger.info("=" * 70)
    logger.info("")
    
    # Step 1: Create a conversation (simulating first run)
    logger.info("Step 1: Creating conversation in 'first session'...")
    logger.info("-" * 70)
    
    memory1 = MemoryManager()
    test_conv_id = f"persistence_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create conversation
    memory1.create_conversation(test_conv_id, title="Persistence Test Conversation")
    logger.info(f"✓ Created conversation: {test_conv_id}")
    
    # Add messages
    memory1.add_message(test_conv_id, "user", "Hello! This is my first message.")
    memory1.add_message(test_conv_id, "assistant", "Hi! I'm here to help.")
    memory1.add_message(test_conv_id, "user", "Can you remember this after restart?")
    memory1.add_message(test_conv_id, "assistant", "Yes, I should be able to remember!")
    
    conversation1 = memory1.get_conversation(test_conv_id)
    logger.info(f"✓ Added {len(conversation1['messages'])} messages")
    logger.info(f"✓ Conversation saved to database")
    logger.info("")
    
    # Step 2: "Restart" - create new memory manager instance (simulating restart)
    logger.info("Step 2: Simulating service restart...")
    logger.info("-" * 70)
    logger.info("  (Creating new MemoryManager instance - like Flask app restart)")
    logger.info("")
    
    # Close first instance (simulating service stop)
    del memory1
    
    # Wait a moment (simulating restart delay)
    time.sleep(0.5)
    
    # Create new instance (simulating service start)
    memory2 = MemoryManager()  # Uses same database
    
    # Verify conversation still exists
    conversation2 = memory2.get_conversation(test_conv_id)
    
    if conversation2:
        logger.info(f"✓ Conversation found after 'restart'!")
        logger.info(f"  ID: {conversation2['id']}")
        logger.info(f"  Title: {conversation2['title']}")
        logger.info(f"  Messages: {len(conversation2['messages'])}")
        logger.info(f"  Created: {conversation2['created_at']}")
        logger.info("")
        
        logger.info("  Message history:")
        for i, msg in enumerate(conversation2['messages'], 1):
            logger.info(f"    {i}. [{msg['role']}]: {msg['content']}")
        logger.info("")
    else:
        logger.error("✗ Conversation NOT found after restart!")
        return False
    
    # Step 3: Add new messages after restart
    logger.info("Step 3: Adding new messages after 'restart'...")
    logger.info("-" * 70)
    
    memory2.add_message(test_conv_id, "user", "Great! You remembered our conversation!")
    memory2.add_message(test_conv_id, "assistant", "Yes! All your messages are still here.")
    
    conversation3 = memory2.get_conversation(test_conv_id)
    logger.info(f"✓ Added 2 more messages")
    logger.info(f"✓ Total messages now: {len(conversation3['messages'])}")
    logger.info("")
    
    # Step 4: Verify with chatbot integration
    if Config.get_llm_api_key():
        logger.info("Step 4: Testing with Chatbot integration...")
        logger.info("-" * 70)
        
        # Create chatbot instance (simulating Flask app startup)
        chatbot = Chatbot(
            use_persistent_memory=True,
            max_history=10
        )
        
        # Load the conversation
        if chatbot.load_conversation(test_conv_id):
            logger.info(f"✓ Chatbot loaded conversation successfully")
            logger.info(f"  Loaded {len(chatbot.conversation_history)} messages into context")
            
            # Send a message that references previous conversation
            response = chatbot.get_response("What did we talk about earlier?")
            logger.info(f"✓ Chatbot response: {response[:100]}...")
            logger.info("")
            
            # Verify it was saved
            final_conv = chatbot.memory_manager.get_conversation(test_conv_id)
            logger.info(f"✓ Final message count: {len(final_conv['messages'])}")
        else:
            logger.error("✗ Failed to load conversation in chatbot")
            return False
    else:
        logger.info("Step 4: Skipping chatbot test (no API key configured)")
        logger.info("")
    
    # Final verification
    logger.info("=" * 70)
    logger.info("Final Verification")
    logger.info("=" * 70)
    
    memory3 = MemoryManager()
    final_conversation = memory3.get_conversation(test_conv_id)
    
    if final_conversation:
        logger.info(f"✓ Conversation persists: {test_conv_id}")
        logger.info(f"  Total messages: {len(final_conversation['messages'])}")
        logger.info(f"  Last updated: {final_conversation['updated_at']}")
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ SUCCESS: Conversations persist across service restarts!")
        logger.info("=" * 70)
        logger.info("")
        logger.info("This means:")
        logger.info("  • When you restart Flask server, conversations are still there")
        logger.info("  • When you restart chatbot CLI, conversations are still there")
        logger.info("  • All messages are saved in the database")
        logger.info("  • Context is maintained across restarts")
        return True
    else:
        logger.error("✗ Final verification failed")
        return False


def show_restart_simulation():
    """Show how Flask app handles restarts."""
    logger.info("\n" + "=" * 70)
    logger.info("How Flask App Handles Restarts")
    logger.info("=" * 70)
    logger.info("")
    logger.info("When Flask app starts:")
    logger.info("  1. MemoryManager connects to database (data/chatbot_memory.db)")
    logger.info("  2. All conversations are already in the database")
    logger.info("  3. API endpoints query database directly:")
    logger.info("     • GET /api/conversations → memory_manager.list_conversations()")
    logger.info("     • GET /api/conversations/<id> → memory_manager.get_conversation(id)")
    logger.info("     • POST /api/chat → saves to database automatically")
    logger.info("")
    logger.info("When you restart Flask:")
    logger.info("  ✓ MemoryManager reconnects to same database")
    logger.info("  ✓ All conversations are immediately available")
    logger.info("  ✓ No data loss")
    logger.info("  ✓ Web UI shows all previous conversations")
    logger.info("")
    logger.info("Database location: data/chatbot_memory.db")
    logger.info("=" * 70)


if __name__ == "__main__":
    success = simulate_restart_test()
    show_restart_simulation()
    
    if success:
        logger.info("\n✅ All persistence tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed")
        sys.exit(1)

