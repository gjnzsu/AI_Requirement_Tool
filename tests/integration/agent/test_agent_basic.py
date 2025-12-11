"""
Test script for LangGraph Agent.

This script tests the agent framework integration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.chatbot import Chatbot
from src.utils.logger import get_logger

logger = get_logger('test.agent')

def test_agent():
    """Test the LangGraph agent."""
    logger.info("=" * 60)
    logger.info("Testing LangGraph Agent")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        # Initialize chatbot with agent enabled
        logger.info("Initializing chatbot with LangGraph agent...")
        chatbot = Chatbot(
            provider_name="openai",  # or "gemini"
            use_agent=True,
            enable_mcp_tools=True,
            use_rag=True
        )
        logger.info("Chatbot initialized successfully!")
        logger.info("")
        
        # Test 1: General conversation
        logger.info("Test 1: General Conversation")
        logger.info("-" * 60)
        response = chatbot.get_response("Hello! How are you?")
        logger.info(f"User: Hello! How are you?")
        logger.info(f"Agent: {response}")
        logger.info("")
        
        # Test 2: Intent detection (Jira creation)
        logger.info("Test 2: Intent Detection - Jira Creation")
        logger.info("-" * 60)
        logger.info("Note: This will attempt to create a Jira issue if configured")
        response = chatbot.get_response("I need to create a Jira ticket for user authentication feature")
        logger.info(f"User: I need to create a Jira ticket for user authentication feature")
        logger.info(f"Agent: {response[:200]}..." if len(response) > 200 else f"Agent: {response}")
        logger.info("")
        
        # Test 3: RAG query (if documents are ingested)
        logger.info("Test 3: RAG Query")
        logger.info("-" * 60)
        response = chatbot.get_response("What is the project about?")
        logger.info(f"User: What is the project about?")
        logger.info(f"Agent: {response[:200]}..." if len(response) > 200 else f"Agent: {response}")
        logger.info("")
        
        logger.info("=" * 60)
        logger.info("All tests completed!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("")
        logger.info("Troubleshooting:")
        logger.info("1. Check that all dependencies are installed: pip install -r requirements.txt")
        logger.info("2. Verify your .env file has API keys configured")
        logger.info("3. Check that LangGraph packages are installed: pip list | Select-String lang")

if __name__ == "__main__":
    test_agent()

