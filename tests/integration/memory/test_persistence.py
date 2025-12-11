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


def simulate_restart_test():
    """Simulate a service restart to verify persistence."""
    print("=" * 70)
    print("Testing Conversation Persistence Across Restarts")
    print("=" * 70)
    print()
    
    # Step 1: Create a conversation (simulating first run)
    print("Step 1: Creating conversation in 'first session'...")
    print("-" * 70)
    
    memory1 = MemoryManager()
    test_conv_id = f"persistence_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create conversation
    memory1.create_conversation(test_conv_id, title="Persistence Test Conversation")
    print(f"✓ Created conversation: {test_conv_id}")
    
    # Add messages
    memory1.add_message(test_conv_id, "user", "Hello! This is my first message.")
    memory1.add_message(test_conv_id, "assistant", "Hi! I'm here to help.")
    memory1.add_message(test_conv_id, "user", "Can you remember this after restart?")
    memory1.add_message(test_conv_id, "assistant", "Yes, I should be able to remember!")
    
    conversation1 = memory1.get_conversation(test_conv_id)
    print(f"✓ Added {len(conversation1['messages'])} messages")
    print(f"✓ Conversation saved to database")
    print()
    
    # Step 2: "Restart" - create new memory manager instance (simulating restart)
    print("Step 2: Simulating service restart...")
    print("-" * 70)
    print("  (Creating new MemoryManager instance - like Flask app restart)")
    print()
    
    # Close first instance (simulating service stop)
    del memory1
    
    # Wait a moment (simulating restart delay)
    time.sleep(0.5)
    
    # Create new instance (simulating service start)
    memory2 = MemoryManager()  # Uses same database
    
    # Verify conversation still exists
    conversation2 = memory2.get_conversation(test_conv_id)
    
    if conversation2:
        print(f"✓ Conversation found after 'restart'!")
        print(f"  ID: {conversation2['id']}")
        print(f"  Title: {conversation2['title']}")
        print(f"  Messages: {len(conversation2['messages'])}")
        print(f"  Created: {conversation2['created_at']}")
        print()
        
        print("  Message history:")
        for i, msg in enumerate(conversation2['messages'], 1):
            print(f"    {i}. [{msg['role']}]: {msg['content']}")
        print()
    else:
        print("✗ Conversation NOT found after restart!")
        return False
    
    # Step 3: Add new messages after restart
    print("Step 3: Adding new messages after 'restart'...")
    print("-" * 70)
    
    memory2.add_message(test_conv_id, "user", "Great! You remembered our conversation!")
    memory2.add_message(test_conv_id, "assistant", "Yes! All your messages are still here.")
    
    conversation3 = memory2.get_conversation(test_conv_id)
    print(f"✓ Added 2 more messages")
    print(f"✓ Total messages now: {len(conversation3['messages'])}")
    print()
    
    # Step 4: Verify with chatbot integration
    if Config.get_llm_api_key():
        print("Step 4: Testing with Chatbot integration...")
        print("-" * 70)
        
        # Create chatbot instance (simulating Flask app startup)
        chatbot = Chatbot(
            use_persistent_memory=True,
            max_history=10
        )
        
        # Load the conversation
        if chatbot.load_conversation(test_conv_id):
            print(f"✓ Chatbot loaded conversation successfully")
            print(f"  Loaded {len(chatbot.conversation_history)} messages into context")
            
            # Send a message that references previous conversation
            response = chatbot.get_response("What did we talk about earlier?")
            print(f"✓ Chatbot response: {response[:100]}...")
            print()
            
            # Verify it was saved
            final_conv = chatbot.memory_manager.get_conversation(test_conv_id)
            print(f"✓ Final message count: {len(final_conv['messages'])}")
        else:
            print("✗ Failed to load conversation in chatbot")
            return False
    else:
        print("Step 4: Skipping chatbot test (no API key configured)")
        print()
    
    # Final verification
    print("=" * 70)
    print("Final Verification")
    print("=" * 70)
    
    memory3 = MemoryManager()
    final_conversation = memory3.get_conversation(test_conv_id)
    
    if final_conversation:
        print(f"✓ Conversation persists: {test_conv_id}")
        print(f"  Total messages: {len(final_conversation['messages'])}")
        print(f"  Last updated: {final_conversation['updated_at']}")
        print()
        print("=" * 70)
        print("✅ SUCCESS: Conversations persist across service restarts!")
        print("=" * 70)
        print()
        print("This means:")
        print("  • When you restart Flask server, conversations are still there")
        print("  • When you restart chatbot CLI, conversations are still there")
        print("  • All messages are saved in the database")
        print("  • Context is maintained across restarts")
        return True
    else:
        print("✗ Final verification failed")
        return False


def show_restart_simulation():
    """Show how Flask app handles restarts."""
    print("\n" + "=" * 70)
    print("How Flask App Handles Restarts")
    print("=" * 70)
    print()
    print("When Flask app starts:")
    print("  1. MemoryManager connects to database (data/chatbot_memory.db)")
    print("  2. All conversations are already in the database")
    print("  3. API endpoints query database directly:")
    print("     • GET /api/conversations → memory_manager.list_conversations()")
    print("     • GET /api/conversations/<id> → memory_manager.get_conversation(id)")
    print("     • POST /api/chat → saves to database automatically")
    print()
    print("When you restart Flask:")
    print("  ✓ MemoryManager reconnects to same database")
    print("  ✓ All conversations are immediately available")
    print("  ✓ No data loss")
    print("  ✓ Web UI shows all previous conversations")
    print()
    print("Database location: data/chatbot_memory.db")
    print("=" * 70)


if __name__ == "__main__":
    success = simulate_restart_test()
    show_restart_simulation()
    
    if success:
        print("\n✅ All persistence tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)

