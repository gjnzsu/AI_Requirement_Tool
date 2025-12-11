"""
Direct test of MCP tool usage in Jira creation.
This bypasses intent detection to directly test the Jira creation handler.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.agent.agent_graph import ChatbotAgent, AgentState
from langchain_core.messages import HumanMessage

async def test_mcp_jira_direct():
    logger = get_logger('test.mcp_jira_direct')

    """Directly test Jira creation with MCP."""
    logger.info("=" * 70)
    logger.info("Direct Test: Jira Creation with MCP")
    logger.info("=" * 70)
    logger.info("")
    
    # Ensure MCP is enabled
    import os
from src.utils.logger import get_logger

    os.environ['USE_MCP'] = 'true'
    
    logger.info("Configuration:")
    logger.info(f"  USE_MCP = {Config.USE_MCP}")
    logger.info("")
    
    # Initialize agent
    logger.info("Initializing agent...")
    agent = ChatbotAgent(
        provider_name=Config.LLM_PROVIDER,
        enable_tools=True,
        use_mcp=True
    )
    logger.info("✓ Agent initialized")
    logger.info("")
    
    # Initialize MCP if needed
    if agent.mcp_integration and not agent.mcp_integration._initialized:
        logger.info("Initializing MCP integration...")
        await agent.mcp_integration.initialize()
        logger.info("✓ MCP initialized")
        logger.info("")
    
    # Create a test state that will trigger Jira creation
    logger.info("=" * 70)
    logger.info("Testing Jira Creation Handler Directly")
    logger.info("=" * 70)
    logger.info("")
    
    test_state: AgentState = {
        "messages": [HumanMessage(content="Create a Jira issue")],
        "user_input": "create jira issue: Test MCP Integration - Summary: Verify MCP tool works, Description: Testing the MCP custom server integration",
        "intent": "jira_creation",  # Force jira_creation intent
        "jira_result": None,
        "evaluation_result": None,
        "confluence_result": None,
        "rag_context": None,
        "conversation_history": [],
        "next_action": None
    }
    
    logger.info("Calling _handle_jira_creation directly...")
    logger.info("")
    
    # Call the handler directly
    result_state = agent._handle_jira_creation(test_state)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Result:")
    logger.info("=" * 70)
    
    jira_result = result_state.get("jira_result")
    if jira_result and jira_result.get("success"):
        logger.info(f"✅ SUCCESS! Jira issue created:")
        logger.info(f"   Key: {jira_result.get('key')}")
        logger.info(f"   Link: {jira_result.get('link')}")
        logger.info(f"   Tool Used: {jira_result.get('tool_used', 'Unknown')}")
        logger.info("")
        
        # Get the response message
        messages = result_state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                logger.info("Response message:")
                logger.info(last_msg.content)
        
        return True
    else:
        logger.error("❌ Failed to create Jira issue")
        if jira_result:
            logger.error(f"   Error: {jira_result.get('error', 'Unknown error')}")
        
        # Show messages
        messages = result_state.get("messages", [])
        if messages:
            logger.info("\nMessages:")
            for msg in messages:
                if hasattr(msg, 'content'):
                    logger.info(f"  - {msg.content[:100]}...")
        
        return False

def main():
    """Main test function."""
    logger.info("\n")
    
    success = asyncio.run(test_mcp_jira_direct())
    
    logger.info("\n" + "=" * 70)
    if success:
        logger.info("✅ Test PASSED - MCP tool was used successfully!")
        logger.info("")
        logger.info("Check the console output above for:")
        logger.info("  - '🚀 Using MCP Tool' (confirms MCP was used)")
        logger.info("  - '✅ MCP Tool SUCCESS' (confirms it worked)")
    else:
        logger.error("❌ Test FAILED")
        logger.error("   Check the output above for error details")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()

