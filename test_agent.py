"""
Test script for LangGraph Agent.

This script tests the agent framework integration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.chatbot import Chatbot

def test_agent():
    """Test the LangGraph agent."""
    print("=" * 60)
    print("Testing LangGraph Agent")
    print("=" * 60)
    print()
    
    try:
        # Initialize chatbot with agent enabled
        print("Initializing chatbot with LangGraph agent...")
        chatbot = Chatbot(
            provider_name="openai",  # or "gemini"
            use_agent=True,
            enable_mcp_tools=True,
            use_rag=True
        )
        print("✓ Chatbot initialized successfully!\n")
        
        # Test 1: General conversation
        print("Test 1: General Conversation")
        print("-" * 60)
        response = chatbot.get_response("Hello! How are you?")
        print(f"User: Hello! How are you?")
        print(f"Agent: {response}\n")
        
        # Test 2: Intent detection (Jira creation)
        print("Test 2: Intent Detection - Jira Creation")
        print("-" * 60)
        print("Note: This will attempt to create a Jira issue if configured")
        response = chatbot.get_response("I need to create a Jira ticket for user authentication feature")
        print(f"User: I need to create a Jira ticket for user authentication feature")
        print(f"Agent: {response[:200]}...\n" if len(response) > 200 else f"Agent: {response}\n")
        
        # Test 3: RAG query (if documents are ingested)
        print("Test 3: RAG Query")
        print("-" * 60)
        response = chatbot.get_response("What is the project about?")
        print(f"User: What is the project about?")
        print(f"Agent: {response[:200]}...\n" if len(response) > 200 else f"Agent: {response}\n")
        
        print("=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Check that all dependencies are installed: pip install -r requirements.txt")
        print("2. Verify your .env file has API keys configured")
        print("3. Check that LangGraph packages are installed: pip list | Select-String lang")

if __name__ == "__main__":
    test_agent()

