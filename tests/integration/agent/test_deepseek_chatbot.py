"""
Test script for DeepSeek Chatbot Integration.

This script tests the chatbot service with DeepSeek model to ensure
full integration works correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.chatbot import Chatbot
from src.utils.logger import get_logger
from config.config import Config

logger = get_logger('test.deepseek.chatbot')

def test_deepseek_chatbot():
    """Test the chatbot with DeepSeek model."""
    logger.info("=" * 80)
    logger.info("DeepSeek Chatbot Integration Test")
    logger.info("=" * 80)
    logger.info("")
    
    # Check configuration
    logger.info("Checking configuration...")
    api_key = Config.DEEPSEEK_API_KEY
    if not api_key:
        logger.error("ERROR: DEEPSEEK_API_KEY not found in configuration")
        logger.info("Set it in .env file or environment variables")
        return False
    
    model = Config.DEEPSEEK_MODEL
    logger.info(f"Provider: deepseek")
    logger.info(f"Model: {model}")
    logger.info(f"API Key: {api_key[:10]}..." if len(api_key) > 10 else "API Key: ***")
    logger.info("")
    
    try:
        # Initialize chatbot with DeepSeek provider
        logger.info("Initializing chatbot with DeepSeek provider...")
        chatbot = Chatbot(
            provider_name="deepseek",
            use_agent=True,
            enable_mcp_tools=False,  # Disable MCP for basic connectivity test
            use_rag=False  # Disable RAG for basic connectivity test
        )
        logger.info("Chatbot initialized successfully!")
        logger.info(f"Provider: {chatbot.provider_name}")
        logger.info("")
        
        # Test 1: Basic conversation
        logger.info("Test 1: Basic Conversation")
        logger.info("-" * 80)
        test_message = "Hello! Please respond with 'DeepSeek chatbot is working correctly!'"
        logger.info(f"User: {test_message}")
        
        try:
            response = chatbot.get_response(test_message)
            logger.info(f"DeepSeek: {response}")
            logger.info("")
            
            # Verify response contains expected content
            if response and len(response) > 0:
                logger.info("✓ Basic conversation test passed")
            else:
                logger.error("✗ Basic conversation test failed - empty response")
                return False
        except Exception as e:
            logger.error(f"✗ Basic conversation test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        logger.info("")
        
        # Test 2: Multi-turn conversation
        logger.info("Test 2: Multi-turn Conversation")
        logger.info("-" * 80)
        try:
            response1 = chatbot.get_response("What is 2+2?")
            logger.info(f"User: What is 2+2?")
            logger.info(f"DeepSeek: {response1}")
            logger.info("")
            
            response2 = chatbot.get_response("What about 3+3?")
            logger.info(f"User: What about 3+3?")
            logger.info(f"DeepSeek: {response2}")
            logger.info("")
            
            if response1 and response2:
                logger.info("✓ Multi-turn conversation test passed")
            else:
                logger.error("✗ Multi-turn conversation test failed")
                return False
        except Exception as e:
            logger.error(f"✗ Multi-turn conversation test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        logger.info("")
        
        # Test 3: Complex query
        logger.info("Test 3: Complex Query")
        logger.info("-" * 80)
        try:
            complex_query = "Explain in one sentence what artificial intelligence is."
            response = chatbot.get_response(complex_query)
            logger.info(f"User: {complex_query}")
            logger.info(f"DeepSeek: {response[:200]}..." if len(response) > 200 else f"DeepSeek: {response}")
            logger.info("")
            
            if response and len(response) > 20:
                logger.info("✓ Complex query test passed")
            else:
                logger.error("✗ Complex query test failed - response too short")
                return False
        except Exception as e:
            logger.error(f"✗ Complex query test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("All DeepSeek chatbot integration tests passed! ✓")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("")
        logger.info("Troubleshooting:")
        logger.info("1. Check that all dependencies are installed: pip install -r requirements.txt")
        logger.info("2. Verify your .env file has DEEPSEEK_API_KEY configured")
        logger.info("3. Check that the API key is valid and has quota")
        logger.info("4. Verify network connectivity to api.deepseek.com")
        return False

if __name__ == "__main__":
    success = test_deepseek_chatbot()
    sys.exit(0 if success else 1)

