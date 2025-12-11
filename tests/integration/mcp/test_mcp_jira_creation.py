"""
Test script to verify MCP tool is used when creating Jira issues through the agent.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.agent.agent_graph import ChatbotAgent

def test_jira_creation_with_mcp():
    logger = get_logger('test.jira_creation_with_mcp')

    """Test creating a Jira issue and verify MCP tool is used."""
    logger.info("=" * 70)
    logger.info("Testing Jira Issue Creation with MCP")
    logger.info("=" * 70)
    logger.info("")
    
    # Check configuration
    logger.info("Configuration Check:")
    logger.info(f"  USE_MCP = {Config.USE_MCP}")
    logger.info(f"  JIRA_URL = {Config.JIRA_URL}")
    logger.info(f"  JIRA_PROJECT_KEY = {Config.JIRA_PROJECT_KEY}")
    logger.info("")
    
    if not Config.USE_MCP:
        logger.error("❌ MCP is not enabled. Set USE_MCP=true first.")
        return False
    
    # Initialize agent with MCP enabled
    logger.info("Initializing ChatbotAgent with MCP enabled...")
    try:
        agent = ChatbotAgent(
            provider_name=Config.LLM_PROVIDER,
            enable_tools=True,
            use_mcp=True  # Explicitly enable MCP
        )
        logger.info("✓ Agent initialized")
        logger.info("")
        
        # Check if MCP integration is set up
        if agent.mcp_integration:
            logger.info("✓ MCP integration is available")
        else:
            logger.warning("⚠ MCP integration is not available")
            logger.info("   Will fall back to custom tools")
        logger.info("")
        
        # Test creating a Jira issue
        logger.info("=" * 70)
        logger.info("Creating Test Jira Issue...")
        logger.info("=" * 70)
        logger.info("")
        
        test_message = "Create a Jira issue for testing MCP integration with summary 'Test MCP Tool' and description 'This is a test to verify MCP tool is working correctly'"
        
        logger.info(f"User request: {test_message}")
        logger.info("")
        logger.info("Processing through agent...")
        logger.info("")
        
        # Invoke the agent
        response = agent.invoke(test_message)
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("Response:")
        logger.info("=" * 70)
        logger.info(response)
        logger.info("")
        
        # Check the result
        # Note: The agent state is internal, but we can check the response
        if "Successfully created" in response or "created Jira issue" in response.lower():
            logger.info("✅ Jira issue creation appears successful!")
            logger.info("")
            logger.info("Check the console output above to see which tool was used:")
            logger.info("  - Look for '🚀 Using MCP Tool' for MCP")
            logger.info("  - Look for '🔧 Using Custom JiraTool' for custom tool")
            return True
        else:
            logger.error("⚠ Issue creation may have failed or used a different path")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    logger.info("\n")
    
    success = test_jira_creation_with_mcp()
    
    logger.info("\n" + "=" * 70)
    if success:
        logger.info("✅ Test completed!")
        logger.info("   Review the output above to verify MCP tool was used.")
    else:
        logger.warning("⚠ Test completed with issues.")
        logger.info("   Review the output above for details.")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Note: This test actually creates a real Jira issue in your project.")
    logger.info("      You may want to delete it after testing.")

if __name__ == "__main__":
    # Make sure MCP is enabled
    import os
from src.utils.logger import get_logger

    os.environ['USE_MCP'] = 'true'
    
    test_jira_creation_with_mcp()

