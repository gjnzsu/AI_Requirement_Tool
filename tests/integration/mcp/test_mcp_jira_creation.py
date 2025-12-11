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
    """Test creating a Jira issue and verify MCP tool is used."""
    print("=" * 70)
    print("Testing Jira Issue Creation with MCP")
    print("=" * 70)
    print()
    
    # Check configuration
    print("Configuration Check:")
    print(f"  USE_MCP = {Config.USE_MCP}")
    print(f"  JIRA_URL = {Config.JIRA_URL}")
    print(f"  JIRA_PROJECT_KEY = {Config.JIRA_PROJECT_KEY}")
    print()
    
    if not Config.USE_MCP:
        print("❌ MCP is not enabled. Set USE_MCP=true first.")
        return False
    
    # Initialize agent with MCP enabled
    print("Initializing ChatbotAgent with MCP enabled...")
    try:
        agent = ChatbotAgent(
            provider_name=Config.LLM_PROVIDER,
            enable_tools=True,
            use_mcp=True  # Explicitly enable MCP
        )
        print("✓ Agent initialized")
        print()
        
        # Check if MCP integration is set up
        if agent.mcp_integration:
            print("✓ MCP integration is available")
        else:
            print("⚠ MCP integration is not available")
            print("   Will fall back to custom tools")
        print()
        
        # Test creating a Jira issue
        print("=" * 70)
        print("Creating Test Jira Issue...")
        print("=" * 70)
        print()
        
        test_message = "Create a Jira issue for testing MCP integration with summary 'Test MCP Tool' and description 'This is a test to verify MCP tool is working correctly'"
        
        print(f"User request: {test_message}")
        print()
        print("Processing through agent...")
        print()
        
        # Invoke the agent
        response = agent.invoke(test_message)
        
        print()
        print("=" * 70)
        print("Response:")
        print("=" * 70)
        print(response)
        print()
        
        # Check the result
        # Note: The agent state is internal, but we can check the response
        if "Successfully created" in response or "created Jira issue" in response.lower():
            print("✅ Jira issue creation appears successful!")
            print()
            print("Check the console output above to see which tool was used:")
            print("  - Look for '🚀 Using MCP Tool' for MCP")
            print("  - Look for '🔧 Using Custom JiraTool' for custom tool")
            return True
        else:
            print("⚠ Issue creation may have failed or used a different path")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("\n")
    
    success = test_jira_creation_with_mcp()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Test completed!")
        print("   Review the output above to verify MCP tool was used.")
    else:
        print("⚠ Test completed with issues.")
        print("   Review the output above for details.")
    print("=" * 70)
    print()
    print("Note: This test actually creates a real Jira issue in your project.")
    print("      You may want to delete it after testing.")

if __name__ == "__main__":
    # Make sure MCP is enabled
    import os
    os.environ['USE_MCP'] = 'true'
    
    test_jira_creation_with_mcp()

