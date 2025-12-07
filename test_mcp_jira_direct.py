"""
Direct test of MCP tool usage in Jira creation.
This bypasses intent detection to directly test the Jira creation handler.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config
from src.agent.agent_graph import ChatbotAgent, AgentState
from langchain_core.messages import HumanMessage

async def test_mcp_jira_direct():
    """Directly test Jira creation with MCP."""
    print("=" * 70)
    print("Direct Test: Jira Creation with MCP")
    print("=" * 70)
    print()
    
    # Ensure MCP is enabled
    import os
    os.environ['USE_MCP'] = 'true'
    
    print("Configuration:")
    print(f"  USE_MCP = {Config.USE_MCP}")
    print()
    
    # Initialize agent
    print("Initializing agent...")
    agent = ChatbotAgent(
        provider_name=Config.LLM_PROVIDER,
        enable_tools=True,
        use_mcp=True
    )
    print("✓ Agent initialized")
    print()
    
    # Initialize MCP if needed
    if agent.mcp_integration and not agent.mcp_integration._initialized:
        print("Initializing MCP integration...")
        await agent.mcp_integration.initialize()
        print("✓ MCP initialized")
        print()
    
    # Create a test state that will trigger Jira creation
    print("=" * 70)
    print("Testing Jira Creation Handler Directly")
    print("=" * 70)
    print()
    
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
    
    print("Calling _handle_jira_creation directly...")
    print()
    
    # Call the handler directly
    result_state = agent._handle_jira_creation(test_state)
    
    print()
    print("=" * 70)
    print("Result:")
    print("=" * 70)
    
    jira_result = result_state.get("jira_result")
    if jira_result and jira_result.get("success"):
        print(f"✅ SUCCESS! Jira issue created:")
        print(f"   Key: {jira_result.get('key')}")
        print(f"   Link: {jira_result.get('link')}")
        print(f"   Tool Used: {jira_result.get('tool_used', 'Unknown')}")
        print()
        
        # Get the response message
        messages = result_state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                print("Response message:")
                print(last_msg.content)
        
        return True
    else:
        print("❌ Failed to create Jira issue")
        if jira_result:
            print(f"   Error: {jira_result.get('error', 'Unknown error')}")
        
        # Show messages
        messages = result_state.get("messages", [])
        if messages:
            print("\nMessages:")
            for msg in messages:
                if hasattr(msg, 'content'):
                    print(f"  - {msg.content[:100]}...")
        
        return False

def main():
    """Main test function."""
    print("\n")
    
    success = asyncio.run(test_mcp_jira_direct())
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Test PASSED - MCP tool was used successfully!")
        print()
        print("Check the console output above for:")
        print("  - '🚀 Using MCP Tool' (confirms MCP was used)")
        print("  - '✅ MCP Tool SUCCESS' (confirms it worked)")
    else:
        print("❌ Test FAILED")
        print("   Check the output above for error details")
    print("=" * 70)

if __name__ == "__main__":
    main()

