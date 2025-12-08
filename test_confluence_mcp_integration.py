"""
Comprehensive test suite for Confluence MCP Integration.

Test Cases:
0. Health check on Atlassian MCP server readiness
1. MCP protocol path is called and logged when creating Confluence page
2. MCP API can retrieve Confluence page info
3. Non-Jira flows don't trigger Confluence MCP API
4. Timeout fallback to direct API with user-friendly message
5. General chat queries about Confluence tooling go to general chat
"""

import sys
import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agent.agent_graph import ChatbotAgent, AgentState
from src.mcp.mcp_integration import MCPIntegration
from langchain_core.messages import HumanMessage, AIMessage
from config.config import Config


class TestConfluenceMCPIntegration(unittest.TestCase):
    """Test suite for Confluence MCP integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.agent = None
        self.mcp_integration = None
    
    def tearDown(self):
        """Clean up after tests."""
        if self.agent:
            del self.agent
        if self.mcp_integration:
            del self.mcp_integration
    
    def test_0_health_check_confluence_mcp_server(self):
        """Test Case 0: Health check on Atlassian MCP server readiness."""
        print("\n" + "="*80)
        print("Test Case 0: Health Check on Atlassian MCP Server Readiness")
        print("="*80)
        
        async def run_health_check():
            self.mcp_integration = MCPIntegration(use_mcp=True)
            await self.mcp_integration.initialize()
            health_status = await self.mcp_integration.check_confluence_mcp_health()
            return health_status
        
        health_status = asyncio.run(run_health_check())
        
        print(f"\nHealth Status:")
        print(f"  Healthy: {health_status.get('healthy', False)}")
        print(f"  Reason: {health_status.get('reason', 'N/A')}")
        print(f"  Confluence Tools Available: {health_status.get('confluence_tools_available', False)}")
        print(f"  Tool Count: {health_status.get('confluence_tool_count', 0)}")
        print(f"  Tool Names: {health_status.get('confluence_tool_names', [])}")
        print(f"  Has Create Page Tool: {health_status.get('has_create_page_tool', False)}")
        print(f"  Has Get Page Tool: {health_status.get('has_get_page_tool', False)}")
        
        # Assert health check returns proper structure
        self.assertIn('healthy', health_status)
        self.assertIn('reason', health_status)
        self.assertIn('confluence_tools_available', health_status)
        
        print("\n[PASS] Test Case 0: PASSED")
        return health_status
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_1_mcp_protocol_called_and_logged(self, mock_config_module, mock_config_agent):
        """Test Case 1: MCP protocol path is called and logged when creating Confluence page."""
        print("\n" + "="*80)
        print("Test Case 1: MCP Protocol Called and Logged for Confluence Creation")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
        mock_config_module.CONFLUENCE_SPACE_KEY = "TEST"
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
        mock_config_agent.CONFLUENCE_SPACE_KEY = "TEST"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        
        # Create agent with mocked MCP integration
        with patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class:
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = True
            mock_mcp_integration.use_mcp = True
            
            # Mock MCP tool
            mock_mcp_tool = MagicMock()
            mock_mcp_tool.name = "create_confluence_page"
            mock_mcp_tool.invoke = Mock(return_value=json.dumps({
                'success': True,
                'id': '12345',
                'title': 'Test Page',
                'link': 'https://test.atlassian.net/wiki/pages/viewpage.action?pageId=12345'
            }))
            
            mock_mcp_integration.get_tool = Mock(return_value=mock_mcp_tool)
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Create agent with mocked LLM to avoid API key issues
            with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
                 patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
                 patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'):
                mock_llm = MagicMock()
                mock_llm_class.return_value = mock_llm
                
                self.agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=True,
                    use_mcp=True
                )
                self.agent.llm = mock_llm  # Use mocked LLM
                self.agent.mcp_integration = mock_mcp_integration
                self.agent.confluence_tool = MagicMock()  # Fallback tool
            
            # Create state with Jira result
            state: AgentState = {
                "messages": [],
                "user_input": "test",
                "intent": "jira_creation",
                "jira_result": {
                    "success": True,
                    "key": "TEST-123",
                    "link": "https://test.atlassian.net/browse/TEST-123",
                    "backlog_data": {
                        "summary": "Test Issue",
                        "business_value": "Test value",
                        "acceptance_criteria": ["AC1", "AC2"],
                        "priority": "Medium"
                    }
                },
                "evaluation_result": {
                    "overall_maturity_score": 75
                },
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Capture print output
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                result_state = self.agent._handle_confluence_creation(state)
            
            output = f.getvalue()
            
            # Verify MCP protocol was called
            self.assertTrue(mock_mcp_integration.get_tool.called, "MCP get_tool should be called")
            self.assertTrue(mock_mcp_tool.invoke.called, "MCP tool invoke should be called")
            
            # Verify logging contains MCP protocol messages
            self.assertIn("MCP PROTOCOL", output, "Output should contain 'MCP PROTOCOL'")
            self.assertIn("Creating Confluence page via MCP tool", output, 
                        "Output should log MCP tool usage")
            
            # Verify result
            self.assertIsNotNone(result_state.get("confluence_result"))
            self.assertTrue(result_state["confluence_result"].get("success"))
            
            print("\n[PASS] Test Case 1: PASSED")
            print(f"  MCP tool was called: {mock_mcp_tool.invoke.called}")
            print(f"  Logging contains 'MCP PROTOCOL': {'MCP PROTOCOL' in output}")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_2_retrieve_confluence_page_info_via_mcp(self, mock_config_module, mock_config_agent):
        """Test Case 2: MCP API can retrieve Confluence page info."""
        print("\n" + "="*80)
        print("Test Case 2: Retrieve Confluence Page Info via MCP API")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
        mock_config_module.CONFLUENCE_SPACE_KEY = "TEST"
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
        mock_config_agent.CONFLUENCE_SPACE_KEY = "TEST"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        
        # Create agent with mocked MCP integration
        with patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class:
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = True
            mock_mcp_integration.use_mcp = True
            
            # Mock MCP retrieval tool
            mock_get_tool = MagicMock()
            mock_get_tool.name = "get_confluence_page"
            mock_get_tool.invoke = Mock(return_value=json.dumps({
                'success': True,
                'id': '12345',
                'title': 'Test Page',
                'link': 'https://test.atlassian.net/wiki/pages/viewpage.action?pageId=12345',
                'content': 'Test page content'
            }))
            
            mock_mcp_integration.get_tool = Mock(return_value=mock_get_tool)
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Create agent with mocked LLM
            with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
                 patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
                 patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'):
                mock_llm = MagicMock()
                mock_llm_class.return_value = mock_llm
                
                self.agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=True,
                    use_mcp=True
                )
                self.agent.llm = mock_llm
                self.agent.mcp_integration = mock_mcp_integration
            
            # Test retrieval
            page_info = self.agent._retrieve_confluence_page_info(page_id="12345")
            
            # Verify MCP tool was called
            self.assertTrue(mock_mcp_integration.get_tool.called)
            self.assertTrue(mock_get_tool.invoke.called)
            
            # Verify result
            self.assertTrue(page_info.get('success'))
            self.assertEqual(page_info.get('id'), '12345')
            self.assertEqual(page_info.get('tool_used'), 'MCP Protocol')
            
            print("\n[PASS] Test Case 2: PASSED")
            print(f"  Retrieved page ID: {page_info.get('id')}")
            print(f"  Tool used: {page_info.get('tool_used')}")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_3_non_jira_flows_dont_trigger_confluence_mcp(self, mock_config_module, mock_config_agent):
        """Test Case 3: Non-Jira flows don't trigger Confluence MCP API."""
        print("\n" + "="*80)
        print("Test Case 3: Non-Jira Flows Don't Trigger Confluence MCP API")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        
        # Create agent with mocked MCP integration
        with patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class:
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = True
            mock_mcp_integration.use_mcp = True
            mock_mcp_integration.get_tool = Mock()
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Create agent with mocked LLM
            with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
                 patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
                 patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'):
                mock_llm = MagicMock()
                mock_llm_class.return_value = mock_llm
                
                self.agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=True,
                    use_mcp=True
                )
                self.agent.llm = mock_llm
                self.agent.mcp_integration = mock_mcp_integration
            
            # Test general chat (should not trigger Confluence MCP)
            state: AgentState = {
                "messages": [],
                "user_input": "What is Python?",
                "intent": "general_chat",
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Process through agent
            result_state = self.agent._handle_general_chat(state)
            
            # Verify MCP get_tool was NOT called for Confluence
            confluence_calls = [call for call in mock_mcp_integration.get_tool.call_args_list 
                              if call and any('confluence' in str(call).lower() or 
                                             'page' in str(call).lower())]
            
            self.assertEqual(len(confluence_calls), 0, 
                           "Confluence MCP should not be called for general chat")
            
            print("\n[PASS] Test Case 3: PASSED")
            print(f"  Confluence MCP calls: {len(confluence_calls)}")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_4_timeout_fallback_to_direct_api(self, mock_config_module, mock_config_agent):
        """Test Case 4: Timeout fallback to direct API with user-friendly message."""
        print("\n" + "="*80)
        print("Test Case 4: Timeout Fallback to Direct API")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
        mock_config_module.CONFLUENCE_SPACE_KEY = "TEST"
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.CONFLUENCE_URL = "https://test.atlassian.net/wiki"
        mock_config_agent.CONFLUENCE_SPACE_KEY = "TEST"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        
        # Create agent with mocked MCP integration that times out
        with patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class:
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = True
            mock_mcp_integration.use_mcp = True
            
            # Mock MCP tool that times out
            import concurrent.futures
            mock_mcp_tool = MagicMock()
            mock_mcp_tool.name = "create_confluence_page"
            # Simulate timeout by raising TimeoutError in the executor
            def timeout_invoke(*args, **kwargs):
                raise concurrent.futures.TimeoutError("MCP timeout")
            mock_mcp_tool.invoke = Mock(side_effect=timeout_invoke)
            
            mock_mcp_integration.get_tool = Mock(return_value=mock_mcp_tool)
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Mock direct API tool that succeeds
            mock_confluence_tool = MagicMock()
            mock_confluence_tool.create_page = Mock(return_value={
                'success': True,
                'id': '12345',
                'title': 'Test Page',
                'link': 'https://test.atlassian.net/wiki/pages/viewpage.action?pageId=12345'
            })
            
            # Create agent with mocked LLM
            with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
                 patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
                 patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'):
                mock_llm = MagicMock()
                mock_llm_class.return_value = mock_llm
                
                self.agent = ChatbotAgent(
                    provider_name="openai",
                    enable_tools=True,
                    use_mcp=True
                )
                self.agent.llm = mock_llm
                self.agent.mcp_integration = mock_mcp_integration
            self.agent.confluence_tool = mock_confluence_tool
            
            # Create state with Jira result
            state: AgentState = {
                "messages": [],
                "user_input": "test",
                "intent": "jira_creation",
                "jira_result": {
                    "success": True,
                    "key": "TEST-123",
                    "link": "https://test.atlassian.net/browse/TEST-123",
                    "backlog_data": {
                        "summary": "Test Issue",
                        "business_value": "Test value",
                        "acceptance_criteria": ["AC1"],
                        "priority": "Medium"
                    }
                },
                "evaluation_result": {},
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Capture output
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                result_state = self.agent._handle_confluence_creation(state)
            
            output = f.getvalue()
            
            # Verify fallback occurred
            self.assertTrue(mock_confluence_tool.create_page.called, 
                          "Direct API should be called after timeout")
            
            # Verify user-friendly message
            messages = result_state.get("messages", [])
            last_message = messages[-1] if messages else None
            if last_message:
                message_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                self.assertIn("Confluence Page Created", message_content or "",
                             "Should contain success message")
            
            # Verify logging shows fallback
            self.assertIn("falling back", output.lower() or "",
                         "Should log fallback to direct API")
            
            print("\n[PASS] Test Case 4: PASSED")
            print(f"  Direct API called: {mock_confluence_tool.create_page.called}")
            print(f"  Fallback logged: {'falling back' in output.lower()}")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_5_confluence_tooling_queries_go_to_general_chat(self, mock_config_module, mock_config_agent):
        """Test Case 5: General chat queries about Confluence tooling go to general chat."""
        print("\n" + "="*80)
        print("Test Case 5: Confluence Tooling Queries Go to General Chat")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        
        # Create agent with mocked LLM
        with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
             patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
             patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'):
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            
            self.agent = ChatbotAgent(
                provider_name="openai",
                enable_tools=True,
                use_mcp=True
            )
            self.agent.llm = mock_llm
        
        # Test various Confluence tooling queries
        test_queries = [
            "what is confluence tool",
            "how does confluence api work",
            "tell me about confluence integration",
            "what is confluence background",
            "explain confluence setup"
        ]
        
        for query in test_queries:
            state: AgentState = {
                "messages": [],
                "user_input": query,
                "intent": None,
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Detect intent
            result_state = self.agent._detect_intent(state)
            detected_intent = result_state.get("intent")
            
            # Verify intent is general_chat
            self.assertEqual(detected_intent, "general_chat",
                           f"Query '{query}' should route to general_chat, got {detected_intent}")
            
            print(f"  [OK] '{query}' -> general_chat")
        
        print("\n[PASS] Test Case 5: PASSED")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_6_jira_creation_workflow_langgraph(self, mock_config_module, mock_config_agent):
        """Test Case 6: Jira creation workflow in LangGraph."""
        print("\n" + "="*80)
        print("Test Case 6: Jira Creation Workflow in LangGraph")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_module.JIRA_URL = "https://test.atlassian.net"
        mock_config_module.JIRA_EMAIL = "test@example.com"
        mock_config_module.JIRA_API_TOKEN = "test-token"
        mock_config_module.JIRA_PROJECT_KEY = "TEST"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.JIRA_URL = "https://test.atlassian.net"
        mock_config_agent.JIRA_EMAIL = "test@example.com"
        mock_config_agent.JIRA_API_TOKEN = "test-token"
        mock_config_agent.JIRA_PROJECT_KEY = "TEST"
        
        # Create agent with mocked components
        with patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class, \
             patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
             patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
             patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'), \
             patch('src.tools.jira_tool.JiraTool') as mock_jira_tool_class:
            
            # Mock MCP integration
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = False
            mock_mcp_integration.use_mcp = True
            mock_mcp_integration.has_tool = Mock(return_value=False)
            mock_mcp_integration.get_tool = Mock(return_value=None)
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Mock LLM
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            
            # Mock Jira tool
            mock_jira_tool = MagicMock()
            mock_jira_tool.create_issue = Mock(return_value={
                'success': True,
                'key': 'TEST-123',
                'link': 'https://test.atlassian.net/browse/TEST-123'
            })
            mock_jira_tool_class.return_value = mock_jira_tool
            
            # Create agent
            self.agent = ChatbotAgent(
                provider_name="openai",
                enable_tools=True,
                use_mcp=True
            )
            self.agent.llm = mock_llm
            self.agent.mcp_integration = mock_mcp_integration
            self.agent.jira_tool = mock_jira_tool
            
            # Test various Jira creation phrases
            test_queries = [
                "pls create a jira ticket",
                "please create a jira ticket",
                "create a jira ticket",
                "create jira issue",
                "new jira ticket",
                "I need to create a jira ticket for a new feature"
            ]
            
            for query in test_queries:
                state: AgentState = {
                    "messages": [],
                    "user_input": query,
                    "intent": None,
                    "jira_result": None,
                    "evaluation_result": None,
                    "confluence_result": None,
                    "rag_context": None,
                    "conversation_history": [],
                    "next_action": None
                }
                
                # Detect intent
                result_state = self.agent._detect_intent(state)
                detected_intent = result_state.get("intent")
                
                # Verify intent is jira_creation
                self.assertEqual(detected_intent, "jira_creation",
                               f"Query '{query}' should route to jira_creation, got {detected_intent}")
                
                print(f"  [OK] '{query[:40]}...' -> jira_creation")
            
            # Test full workflow invocation (mocked)
            test_query = "pls create a jira ticket. the requirement is 'integrate MCP server'"
            
            # Mock LLM response for backlog generation
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "summary": "Integrate MCP Server",
                "description": "Integrate MCP server for Confluence",
                "business_value": "Improve integration",
                "acceptance_criteria": ["AC1", "AC2"],
                "priority": "Medium",
                "invest_analysis": "Good"
            })
            mock_llm.invoke = Mock(return_value=mock_response)
            
            # Test that the workflow would route correctly
            initial_state: AgentState = {
                "messages": [],
                "user_input": test_query,
                "intent": None,
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Detect intent
            state_after_intent = self.agent._detect_intent(initial_state)
            self.assertEqual(state_after_intent.get("intent"), "jira_creation",
                           "Should detect jira_creation intent")
            
            print(f"\n  [OK] Full workflow test: '{test_query[:50]}...'")
            print(f"       Intent detected: {state_after_intent.get('intent')}")
            
            print("\n[PASS] Test Case 6: PASSED")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_7_basic_model_call_works(self, mock_config_module, mock_config_agent):
        """Test Case 7: Basic model call function works correctly."""
        print("\n" + "="*80)
        print("Test Case 7: Basic Model Call Function Works")
        print("="*80)
        
        # Mock configuration with proper string values
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        
        # Create agent with mocked LLM
        with patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
             patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class:
            
            # Mock LLM that returns a successful response
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Hello! How can I help you today?"
            mock_llm.invoke = Mock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm
            
            # Mock MCP integration
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = False
            mock_mcp_integration.use_mcp = True
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Create agent
            self.agent = ChatbotAgent(
                provider_name="openai",
                enable_tools=True,
                use_mcp=True
            )
            self.agent.llm = mock_llm
            self.agent.mcp_integration = mock_mcp_integration
            
            # Test simple greeting
            state: AgentState = {
                "messages": [],
                "user_input": "hi",
                "intent": "general_chat",
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Handle general chat
            result_state = self.agent._handle_general_chat(state)
            
            # Verify LLM was called
            self.assertTrue(mock_llm.invoke.called, "LLM invoke should be called")
            
            # Verify response was added to messages
            messages = result_state.get("messages", [])
            self.assertGreater(len(messages), 0, "Should have messages in state")
            
            # Check that last message is an AI response
            last_message = messages[-1]
            if hasattr(last_message, 'content'):
                self.assertIn("Hello", last_message.content or "", 
                            "Should contain greeting response")
            
            print(f"  [OK] LLM was called: {mock_llm.invoke.called}")
            print(f"  [OK] Response generated: {len(messages)} messages in state")
            
            # Test error handling - connection error
            mock_llm.invoke = Mock(side_effect=Exception("Connection error."))
            
            state_error: AgentState = {
                "messages": [],
                "user_input": "hello",
                "intent": "general_chat",
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Should handle error gracefully
            result_state_error = self.agent._handle_general_chat(state_error)
            
            # Verify error was handled
            messages_error = result_state_error.get("messages", [])
            self.assertGreater(len(messages_error), 0, "Should have error message")
            
            last_message_error = messages_error[-1]
            if hasattr(last_message_error, 'content'):
                error_content = last_message_error.content or ""
                self.assertIn("apologize", error_content.lower(), 
                            "Should contain apology message")
                self.assertIn("connection", error_content.lower(), 
                            "Should mention connection issue")
            
            print(f"  [OK] Error handling works: connection error handled gracefully")
            
            print("\n[PASS] Test Case 7: PASSED")
    
    @patch('src.agent.agent_graph.Config')
    @patch('config.config.Config')
    def test_8_jira_creation_timeout_handling(self, mock_config_module, mock_config_agent):
        """Test Case 8: Jira creation timeout handling and fallback."""
        print("\n" + "="*80)
        print("Test Case 8: Jira Creation Timeout Handling")
        print("="*80)
        
        # Mock configuration
        mock_config_module.USE_MCP = True
        mock_config_module.OPENAI_API_KEY = "test-key"
        mock_config_module.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_module.JIRA_URL = "https://test.atlassian.net"
        mock_config_module.JIRA_EMAIL = "test@example.com"
        mock_config_module.JIRA_API_TOKEN = "test-token"
        mock_config_module.JIRA_PROJECT_KEY = "TEST"
        mock_config_agent.USE_MCP = True
        mock_config_agent.OPENAI_API_KEY = "test-key"
        mock_config_agent.OPENAI_MODEL = "gpt-3.5-turbo"
        mock_config_agent.JIRA_URL = "https://test.atlassian.net"
        mock_config_agent.JIRA_EMAIL = "test@example.com"
        mock_config_agent.JIRA_API_TOKEN = "test-token"
        mock_config_agent.JIRA_PROJECT_KEY = "TEST"
        
        # Create agent with mocked components
        with patch('src.agent.agent_graph.MCPIntegration') as mock_mcp_class, \
             patch('src.agent.agent_graph.ChatOpenAI') as mock_llm_class, \
             patch('src.agent.agent_graph.Config.OPENAI_API_KEY', 'test-key'), \
             patch('src.agent.agent_graph.Config.OPENAI_MODEL', 'gpt-3.5-turbo'), \
             patch('src.tools.jira_tool.JiraTool') as mock_jira_tool_class:
            
            # Mock MCP integration
            mock_mcp_integration = MagicMock()
            mock_mcp_integration._initialized = True
            mock_mcp_integration.use_mcp = True
            mock_mcp_integration.has_tool = Mock(return_value=True)
            
            # Mock MCP tool that times out
            mock_mcp_tool = MagicMock()
            mock_mcp_tool.name = "create_jira_issue"
            # Simulate timeout by returning error string
            mock_mcp_tool.invoke = Mock(return_value="Error: Tool 'create_jira_issue' execution timed out after 60 seconds. The MCP server may be slow or unresponsive.")
            mock_mcp_integration.get_tool = Mock(return_value=mock_mcp_tool)
            mock_mcp_class.return_value = mock_mcp_integration
            
            # Mock LLM
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "summary": "Test Issue",
                "description": "Test description",
                "priority": "Medium"
            })
            mock_llm.invoke = Mock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm
            
            # Mock Jira tool that succeeds (fallback)
            mock_jira_tool = MagicMock()
            mock_jira_tool.create_issue = Mock(return_value={
                'success': True,
                'key': 'TEST-123',
                'link': 'https://test.atlassian.net/browse/TEST-123'
            })
            mock_jira_tool_class.return_value = mock_jira_tool
            
            # Create agent
            self.agent = ChatbotAgent(
                provider_name="openai",
                enable_tools=True,
                use_mcp=True
            )
            self.agent.llm = mock_llm
            self.agent.mcp_integration = mock_mcp_integration
            self.agent.jira_tool = mock_jira_tool
            
            # Create state
            state: AgentState = {
                "messages": [],
                "user_input": "create a jira ticket",
                "intent": "jira_creation",
                "jira_result": None,
                "evaluation_result": None,
                "confluence_result": None,
                "rag_context": None,
                "conversation_history": [],
                "next_action": None
            }
            
            # Handle Jira creation
            result_state = self.agent._handle_jira_creation(state)
            
            # Verify MCP tool was called
            self.assertTrue(mock_mcp_tool.invoke.called, "MCP tool should be called")
            
            # Verify fallback to custom tool was attempted
            self.assertTrue(mock_jira_tool.create_issue.called, "Custom tool should be called as fallback")
            
            # Verify result is successful (via fallback)
            jira_result = result_state.get("jira_result", {})
            self.assertTrue(jira_result.get("success"), "Should succeed via fallback")
            self.assertEqual(jira_result.get("key"), "TEST-123")
            
            # Verify user-friendly message
            messages = result_state.get("messages", [])
            last_message = messages[-1] if messages else None
            if last_message and hasattr(last_message, 'content'):
                content = last_message.content or ""
                self.assertIn("Successfully created", content, "Should show success message")
            
            print(f"  [OK] MCP tool timeout handled: {mock_mcp_tool.invoke.called}")
            print(f"  [OK] Fallback to custom tool: {mock_jira_tool.create_issue.called}")
            print(f"  [OK] Issue created successfully: {jira_result.get('key')}")
            
            print("\n[PASS] Test Case 8: PASSED")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*80)
    print("Confluence MCP Integration Test Suite")
    print("="*80)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_cases = [
        'test_0_health_check_confluence_mcp_server',
        'test_1_mcp_protocol_called_and_logged',
        'test_2_retrieve_confluence_page_info_via_mcp',
        'test_3_non_jira_flows_dont_trigger_confluence_mcp',
        'test_4_timeout_fallback_to_direct_api',
        'test_5_confluence_tooling_queries_go_to_general_chat',
        'test_6_jira_creation_workflow_langgraph',
        'test_7_basic_model_call_works',
        'test_8_jira_creation_timeout_handling'
    ]
    
    for test_case in test_cases:
        suite.addTest(TestConfluenceMCPIntegration(test_case))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

