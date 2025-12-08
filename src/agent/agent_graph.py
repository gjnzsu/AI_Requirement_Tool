"""
LangGraph Agent for Chatbot with Tool Orchestration.

This agent uses LangGraph to intelligently route user requests and orchestrate
tools (Jira, Confluence, RAG) based on user intent.
"""

from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import sys
import concurrent.futures
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.jira_tool import JiraTool
from src.tools.confluence_tool import ConfluenceTool
from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.mcp.mcp_integration import MCPIntegration
from config.config import Config


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[List[BaseMessage], "Conversation messages"]
    user_input: str
    intent: Optional[str]  # 'jira_creation', 'general_chat', 'rag_query', etc.
    jira_result: Optional[Dict[str, Any]]
    evaluation_result: Optional[Dict[str, Any]]
    confluence_result: Optional[Dict[str, Any]]
    rag_context: Optional[List[str]]
    conversation_history: List[Dict[str, str]]
    next_action: Optional[str]  # Next node to execute


class ChatbotAgent:
    """
    LangGraph-based agent for intelligent chatbot with tool orchestration.
    """
    
    def __init__(self, 
                 provider_name: str = "openai",
                 model: Optional[str] = None,
                 temperature: float = 0.7,
                 enable_tools: bool = True,
                 rag_service: Optional[Any] = None,
                 use_mcp: Optional[bool] = None):
        """
        Initialize the LangGraph agent.
        
        Args:
            provider_name: LLM provider ('openai' or 'gemini')
            model: Model name (if None, uses default from Config)
            temperature: Sampling temperature
            enable_tools: Whether to enable Jira/Confluence tools
            rag_service: Optional RAG service instance
            use_mcp: Whether to use MCP protocol for tools (None = use Config.USE_MCP)
        """
        self.provider_name = provider_name.lower()
        self.temperature = temperature
        self.enable_tools = enable_tools
        # Use config value if not explicitly provided
        self.use_mcp = use_mcp if use_mcp is not None else Config.USE_MCP
        self._rag_service = rag_service
        
        # Initialize LLM
        self.llm = self._initialize_llm(model)
        
        # Initialize MCP integration if enabled
        self.mcp_integration = None
        if self.use_mcp:
            try:
                self.mcp_integration = MCPIntegration(use_mcp=True)
                # Initialize MCP asynchronously (will be done on first use)
                print("✓ MCP integration enabled - will initialize on first use")
            except Exception as e:
                print(f"⚠ Failed to initialize MCP integration: {e}")
                print("   Falling back to custom tools")
                self.use_mcp = False
                self.mcp_integration = None
        
        # Initialize tools (always initialize custom tools as fallback)
        self.jira_tool = None
        self.confluence_tool = None
        self.jira_evaluator = None
        
        if self.enable_tools:
            self._initialize_tools()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _initialize_llm(self, model: Optional[str] = None):
        """Initialize the LLM based on provider."""
        if self.provider_name == "openai":
            api_key = Config.OPENAI_API_KEY
            model_name = model or Config.OPENAI_MODEL
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in configuration")
            
            # Validate API key format (should start with 'sk-')
            if not api_key.startswith('sk-'):
                print(f"⚠ Warning: OpenAI API key format may be invalid (should start with 'sk-')")
            
            # Validate model name (fix common issues)
            if model_name == "gpt-4.1":
                print(f"⚠ Warning: Model 'gpt-4.1' may be invalid. Using 'gpt-4' instead.")
                model_name = "gpt-4"
            elif "gpt-4" not in model_name.lower() and "gpt-3.5" not in model_name.lower():
                print(f"⚠ Warning: Model '{model_name}' may not be valid. Common models: gpt-4, gpt-4-turbo, gpt-3.5-turbo")
            
            try:
                # Try with timeout and max_retries (LangChain 0.1.0+)
                llm = ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                    timeout=15.0,  # Reduced timeout to 15 seconds
                    max_retries=1  # Reduced retries to 1 to avoid long waits
                )
                print(f"✓ LLM initialized: {self.provider_name} ({model_name})")
                return llm
            except TypeError:
                # Fallback if parameters not supported
                print(f"⚠ LLM timeout parameter not supported, using default")
                return ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key
                )
            except Exception as e:
                print(f"⚠ LLM initialization error: {e}")
                raise
        elif self.provider_name == "gemini":
            api_key = Config.GEMINI_API_KEY
            model_name = model or Config.GEMINI_MODEL
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in configuration")
            try:
                # Try with timeout and max_retries
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=self.temperature,
                    google_api_key=api_key,
                    timeout=30.0,  # Add timeout to LLM calls
                    max_retries=2  # Limit retries to avoid long waits
                )
            except TypeError:
                # Fallback if parameters not supported
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=self.temperature,
                    google_api_key=api_key
                )
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
    
    def _initialize_tools(self):
        """Initialize Jira and Confluence tools."""
        try:
            self.jira_tool = JiraTool()
        except Exception as e:
            print(f"⚠ Failed to initialize Jira Tool: {e}")
        
        try:
            self.confluence_tool = ConfluenceTool()
        except Exception as e:
            print(f"⚠ Failed to initialize Confluence Tool: {e}")
        
        # Initialize Jira evaluator if Jira tool is available
        if self.jira_tool:
            try:
                from src.llm import LLMRouter
                llm_provider = LLMRouter.get_provider(
                    provider_name=self.provider_name,
                    api_key=Config.OPENAI_API_KEY if self.provider_name == "openai" else Config.GEMINI_API_KEY,
                    model=Config.OPENAI_MODEL if self.provider_name == "openai" else Config.GEMINI_MODEL
                )
                self.jira_evaluator = JiraMaturityEvaluator(
                    jira_url=Config.JIRA_URL,
                    jira_email=Config.JIRA_EMAIL,
                    jira_api_token=Config.JIRA_API_TOKEN,
                    project_key=Config.JIRA_PROJECT_KEY,
                    llm_provider=llm_provider
                )
            except Exception as e:
                print(f"⚠ Failed to initialize Jira Evaluator: {e}")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("intent_detection", self._detect_intent)
        graph.add_node("general_chat", self._handle_general_chat)
        graph.add_node("jira_creation", self._handle_jira_creation)
        graph.add_node("evaluation", self._handle_evaluation)
        graph.add_node("confluence_creation", self._handle_confluence_creation)
        graph.add_node("rag_query", self._handle_rag_query)
        
        # Set entry point
        graph.set_entry_point("intent_detection")
        
        # Add conditional edges
        graph.add_conditional_edges(
            "intent_detection",
            self._route_after_intent,
            {
                "jira_creation": "jira_creation",
                "rag_query": "rag_query",
                "general_chat": "general_chat",
                "end": END
            }
        )
        
        # Jira creation workflow
        graph.add_edge("jira_creation", "evaluation")
        graph.add_conditional_edges(
            "evaluation",
            self._route_after_evaluation,
            {
                "confluence_creation": "confluence_creation",
                "end": END
            }
        )
        graph.add_edge("confluence_creation", END)
        
        # RAG and general chat go directly to END
        graph.add_edge("rag_query", END)
        graph.add_edge("general_chat", END)
        
        return graph.compile()
    
    def _detect_intent(self, state: AgentState) -> AgentState:
        """Detect user intent from the input with comprehensive keyword-based detection."""
        user_input = state.get("user_input", "").lower()
        messages = state.get("messages", [])
        print(f"🔍 LangGraph: Detecting intent for input: '{user_input[:50]}...'")
        
        # Comprehensive keyword-based detection (avoid LLM call when possible)
        # Include variations with articles (a, an, the) and common phrases
        jira_creation_keywords = [
            'create jira', 'create issue', 'create ticket', 'create backlog',
            'create a jira', 'create an issue', 'create a ticket', 'create a backlog',
            'create the jira', 'create the issue', 'create the ticket',
            'new jira', 'new issue', 'new ticket', 'new backlog',
            'add jira', 'add issue', 'add ticket',
            'make jira', 'make issue', 'make ticket',
            'jira ticket', 'jira issue', 'jira backlog',
            'open jira', 'open issue', 'open ticket',
            'generate jira', 'generate issue', 'generate ticket',
            'submit jira', 'submit issue', 'submit ticket'
        ]
        
        # Expanded RAG keywords for knowledge/documentation queries
        rag_keywords = ['what is', 'what are', 'how to', 'how do', 'explain', 'tell me about',
                       'document', 'documentation', 'guide', 'help with', 'information about',
                       'describe', 'definition', 'meaning', 'example']
        
        # General chat keywords (simple questions, greetings)
        general_chat_keywords = ['hello', 'hi', 'hey', 'who are you', 'what are you',
                                'how are you', 'thanks', 'thank you', 'bye', 'goodbye',
                                'help', 'assist', 'chat', 'talk']
        
        # Confluence tooling background queries - route to general chat
        confluence_tooling_keywords = ['confluence tool', 'confluence api', 'confluence integration',
                                      'how does confluence', 'what is confluence tool',
                                      'confluence background', 'confluence setup', 'confluence config']
        
        # Check for Confluence tooling background queries first (route to general chat)
        if any(keyword in user_input for keyword in confluence_tooling_keywords):
            state["intent"] = "general_chat"
            print(f"  → Intent: general_chat (Confluence tooling query)")
            return state
        
        # Check for Jira creation intent keywords
        # Use more flexible matching - check if any keyword appears in the input
        # Also check for common patterns like "create a jira ticket", "pls create jira", etc.
        jira_patterns = [
            r'\b(create|make|add|new|open|generate|submit)\s+(a\s+)?(jira|issue|ticket|backlog)',
            r'\b(jira|issue|ticket)\s+(create|creation|ticket|issue)',
            r'pls\s+create\s+(a\s+)?(jira|issue|ticket)',
            r'please\s+create\s+(a\s+)?(jira|issue|ticket)'
        ]
        
        # First try simple keyword matching (faster)
        if any(keyword in user_input for keyword in jira_creation_keywords):
            # Check if we have either custom tool or MCP tool available
            has_jira_capability = self.jira_tool or (self.use_mcp and self.mcp_integration)
            if has_jira_capability:
                state["intent"] = "jira_creation"
                print(f"  → Intent: jira_creation (keyword match)")
                return state
        
        # Then try regex patterns for more complex phrases
        import re
        for pattern in jira_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                # Check if we have either custom tool or MCP tool available
                has_jira_capability = self.jira_tool or (self.use_mcp and self.mcp_integration)
                if has_jira_capability:
                    state["intent"] = "jira_creation"
                    print(f"  → Intent: jira_creation (pattern match: {pattern})")
                    return state
        
        # Check for RAG intent keywords (knowledge/documentation queries)
        if any(keyword in user_input for keyword in rag_keywords):
            state["intent"] = "rag_query"
            print(f"  → Intent: rag_query (keyword match)")
            return state
        
        # Check for general chat keywords (simple questions, greetings)
        if any(keyword in user_input for keyword in general_chat_keywords):
            state["intent"] = "general_chat"
            print(f"  → Intent: general_chat (keyword match)")
            return state
        
        # For ambiguous cases, default to general_chat (skip LLM to avoid timeout)
        # LLM-based detection is unreliable and slow, so we use keyword-based only
        state["intent"] = "general_chat"
        print(f"  → Intent: general_chat (default)")
        return state
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Route to appropriate node based on detected intent."""
        intent = state.get("intent", "general_chat")
        
        # For general chat and RAG queries, don't initialize MCP - it's not needed
        if intent in ["general_chat", "rag_query"]:
            return intent
        
        # Only check for Jira tools if intent is jira_creation
        # Only route to jira_creation if we have tools available (MCP or custom)
        has_jira_tool = False
        if intent == "jira_creation":
            # Check custom tool first (no initialization needed)
            if self.jira_tool:
                has_jira_tool = True
            # Then check MCP tool (only initialize if needed)
            elif self.use_mcp and self.mcp_integration:
                # Don't initialize here - let _handle_jira_creation do it
                # Just check if it's already initialized and has the tool
                if self.mcp_integration._initialized:
                    if self.mcp_integration.has_tool('create_jira_issue'):
                        has_jira_tool = True
                else:
                    # MCP not initialized yet, but we have MCP enabled
                    # Will initialize in _handle_jira_creation
                    has_jira_tool = True  # Assume it will be available after init
        
        if intent == "jira_creation" and has_jira_tool:
            return "jira_creation"
        elif intent == "rag_query":
            return "rag_query"
        else:
            return "general_chat"
    
    def _retrieve_confluence_page_info(self, page_id: str = None, page_title: str = None) -> Dict[str, Any]:
        """
        Retrieve Confluence page information using MCP API.
        
        Args:
            page_id: Confluence page ID
            page_title: Confluence page title (alternative to page_id)
            
        Returns:
            Dictionary with page information or error
        """
        use_mcp = self.use_mcp and self.mcp_integration is not None
        
        if not use_mcp:
            return {'success': False, 'error': 'MCP not enabled'}
        
        # Initialize MCP if needed (with timeout to prevent blocking)
        if not self.mcp_integration._initialized:
            try:
                import asyncio
                import concurrent.futures
                # Initialize with timeout to prevent blocking
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.mcp_integration.initialize())
                    try:
                        future.result(timeout=15.0)  # 15 second timeout for initialization
                    except concurrent.futures.TimeoutError:
                        return {'success': False, 'error': 'MCP initialization timeout'}
            except Exception as e:
                return {'success': False, 'error': f'MCP initialization failed: {str(e)}'}
        
        # Try to find MCP tool for retrieving Confluence pages
        mcp_tool_names = ['get_confluence_page', 'confluence_get_page', 'get_page', 
                         'confluence_page_get', 'read_confluence_page', 'confluence_read_page']
        mcp_tool = None
        
        for tool_name in mcp_tool_names:
            mcp_tool = self.mcp_integration.get_tool(tool_name)
            if mcp_tool:
                print(f"✓ Found MCP Confluence retrieval tool: {tool_name}")
                break
        
        if not mcp_tool:
            return {'success': False, 'error': 'MCP Confluence retrieval tool not available'}
        
        try:
            print(f"🚀 [MCP PROTOCOL] Retrieving Confluence page info...")
            print(f"   MCP Tool: {mcp_tool.name}")
            if page_id:
                print(f"   Page ID: {page_id}")
            if page_title:
                print(f"   Page Title: {page_title}")
            
            # Prepare arguments
            mcp_args = {}
            if page_id:
                mcp_args['page_id'] = page_id
            if page_title:
                mcp_args['title'] = page_title
            if not mcp_args:
                return {'success': False, 'error': 'Either page_id or page_title must be provided'}
            
            # Call MCP tool with timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(mcp_tool.invoke, mcp_args)
                try:
                    mcp_result = future.result(timeout=30.0)
                    
                    # Parse result
                    if isinstance(mcp_result, str):
                        import json
                        try:
                            if mcp_result.strip().startswith('```'):
                                lines = mcp_result.split('\n')
                                json_lines = [line for line in lines 
                                             if not line.strip().startswith('```')]
                                mcp_result = '\n'.join(json_lines)
                            mcp_data = json.loads(mcp_result)
                        except json.JSONDecodeError:
                            # If not JSON, return as text
                            return {'success': True, 'content': mcp_result, 'tool_used': 'MCP Protocol'}
                    elif isinstance(mcp_result, dict):
                        mcp_data = mcp_result
                    else:
                        return {'success': False, 'error': f'Unexpected result type: {type(mcp_result)}'}
                    
                    if isinstance(mcp_data, dict):
                        mcp_data['tool_used'] = 'MCP Protocol'
                        return mcp_data
                    
                except concurrent.futures.TimeoutError:
                    return {'success': False, 'error': 'MCP tool call timeout after 30 seconds'}
                    
        except Exception as e:
            return {'success': False, 'error': f'MCP tool call failed: {str(e)}'}
    
    def _handle_general_chat(self, state: AgentState) -> AgentState:
        """Handle general conversation."""
        messages = state.get("messages", [])
        user_input = state.get("user_input", "")
        
        # Check if user is asking about a Confluence page (e.g., "what is the confluence page for PROJ-123")
        # Extract potential page references from user input
        import re
        confluence_page_patterns = [
            r'confluence page (?:for|about|of) ([A-Z]+-\d+)',  # "confluence page for PROJ-123"
            r'confluence page (?:with )?(?:id|page[_\s]?id)[\s:=]+(\d+)',  # "confluence page id 12345"
            r'confluence page (?:titled|title)[\s:]+(.+?)(?:\?|$)',  # "confluence page titled X"
        ]
        
        page_id = None
        page_title = None
        
        for pattern in confluence_page_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                if 'id' in pattern.lower():
                    page_id = match.group(1)
                elif 'title' in pattern.lower():
                    page_title = match.group(1).strip()
                else:
                    # Could be a Jira issue key, try to get Confluence page from state
                    issue_key = match.group(1)
                    # Check if we have confluence_result in state from previous creation
                    confluence_result = state.get("confluence_result")
                    if confluence_result and confluence_result.get('success'):
                        page_id = confluence_result.get('id')
                        page_title = confluence_result.get('title')
                break
        
        # If we found a page reference, try to retrieve it using MCP
        if page_id or page_title:
            print(f"🔍 Detected Confluence page query, attempting MCP retrieval...")
            page_info = self._retrieve_confluence_page_info(page_id=page_id, page_title=page_title)
            
            if page_info.get('success'):
                # Add page info to context
                page_context = f"\n\nConfluence Page Information (retrieved via MCP Protocol):\n"
                page_context += f"Title: {page_info.get('title', 'N/A')}\n"
                page_context += f"Link: {page_info.get('link', 'N/A')}\n"
                if page_info.get('content'):
                    content_preview = str(page_info.get('content', ''))[:500]
                    page_context += f"Content Preview: {content_preview}...\n"
                user_input = user_input + page_context
                print(f"✓ Retrieved Confluence page info via MCP Protocol")
            else:
                print(f"⚠ Could not retrieve Confluence page via MCP: {page_info.get('error', 'Unknown error')}")
        
        # Add system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(
                content="You are a helpful, friendly, and knowledgeable AI assistant. "
                       "You provide clear, concise, and accurate responses."
            )
            messages = [system_msg] + messages
        
        # Add user message
        messages.append(HumanMessage(content=user_input))
        
        # Generate response with timeout
        try:
            # Test if LLM is working with a simple call first
            import time
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.llm.invoke, messages)
                try:
                    response = future.result(timeout=20.0)  # 20 second timeout (reduced from 30s)
                    elapsed = time.time() - start_time
                    print(f"✓ LLM response received in {elapsed:.2f}s")
                    messages.append(response)
                    state["messages"] = messages
                except concurrent.futures.TimeoutError:
                    elapsed = time.time() - start_time
                    print(f"⚠ LLM response timeout ({elapsed:.2f}s) for general chat")
                    print(f"   Check: API key validity, network connection, model name")
                    error_msg = AIMessage(
                        content="I apologize, but the request timed out. Please check your API key and network connection. The API may be slow or unavailable."
                    )
                    messages.append(error_msg)
                    state["messages"] = messages
                except Exception as executor_error:
                    # Handle errors from the executor (like connection errors)
                    elapsed = time.time() - start_time
                    error_type = type(executor_error).__name__
                    error_str = str(executor_error).lower()
                    print(f"⚠ LLM call error after {elapsed:.2f}s: {executor_error}")
                    print(f"   Error type: {error_type}")
                    
                    # Detect error category by checking both type name and error message
                    is_connection_error = (
                        'Connection' in error_type or 
                        'connection' in error_str or
                        'connect' in error_str or
                        'network' in error_str or
                        'unreachable' in error_str or
                        'timeout' in error_str
                    )
                    is_auth_error = (
                        'Authentication' in error_type or 
                        'auth' in error_str or 
                        'api key' in error_str or
                        'unauthorized' in error_str or
                        'invalid' in error_str and 'key' in error_str
                    )
                    is_rate_limit_error = (
                        'RateLimit' in error_type or 
                        'rate limit' in error_str or
                        'rate_limit' in error_str
                    )
                    
                    # Provide user-friendly error messages based on error category
                    if is_connection_error:
                        user_message = (
                            "I apologize, but I'm having trouble connecting to the AI service. "
                            "This could be due to:\n"
                            "- Network connectivity issues\n"
                            "- API service temporarily unavailable\n"
                            "- Firewall or proxy settings\n\n"
                            "Please check your network connection and try again."
                        )
                        # Don't print traceback for connection errors - they're common and expected
                        print(f"   → Connection error detected, providing user-friendly message")
                    elif is_auth_error:
                        user_message = (
                            "I apologize, but there's an authentication issue. "
                            "Please check that your API key is correctly configured and has the necessary permissions."
                        )
                        print(f"   → Authentication error detected")
                    elif is_rate_limit_error:
                        user_message = (
                            "I apologize, but the API rate limit has been exceeded. "
                            "Please wait a moment and try again."
                        )
                        print(f"   → Rate limit error detected")
                    else:
                        # Generic error message for unexpected errors
                        user_message = (
                            f"I apologize, but I encountered an error. "
                            "Please check your API key and network connection, or try again later."
                        )
                        # Print traceback for unexpected errors to help with debugging
                        import traceback
                        traceback.print_exc()
                    
                    error_msg = AIMessage(content=user_message)
                    messages.append(error_msg)
                    state["messages"] = messages
        except Exception as e:
            # Catch any other unexpected errors
            error_type = type(e).__name__
            print(f"⚠ Unexpected error in general chat: {e}")
            print(f"   Error type: {error_type}")
            
            # Provide a generic but helpful error message
            error_msg = AIMessage(
                content="I apologize, but I encountered an unexpected error. Please try again, or check your configuration if the problem persists."
            )
            messages.append(error_msg)
            state["messages"] = messages
            
            # Print traceback for unexpected errors
            import traceback
            traceback.print_exc()
        
        return state
    
    def _handle_jira_creation(self, state: AgentState) -> AgentState:
        """Handle Jira issue creation."""
        import datetime
        
        print("=" * 70)
        print("🔧 Jira Creation: Checking available tools...")
        print(f"   Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Try to use MCP if enabled and available, otherwise fall back to custom tools
        use_mcp = self.use_mcp and self.mcp_integration is not None
        
        if self.use_mcp:
            print(f"✓ MCP is enabled (USE_MCP={self.use_mcp})")
        else:
            print(f"⚠ MCP is disabled (USE_MCP={self.use_mcp})")
        
        # Initialize MCP if needed (lazy initialization)
        if use_mcp and not self.mcp_integration._initialized:
            print("🔄 Initializing MCP integration (lazy initialization)...")
            try:
                import asyncio
                asyncio.run(self.mcp_integration.initialize())
                print("✓ MCP integration initialized successfully")
            except Exception as e:
                print(f"✗ MCP initialization failed: {e}")
                print("   Falling back to custom tools")
                use_mcp = False
        
        # Check if we have MCP tools available
        mcp_jira_tool = None
        if use_mcp:
            mcp_jira_tool = self.mcp_integration.get_tool('create_jira_issue')
            if not mcp_jira_tool:
                print("⚠ MCP tool 'create_jira_issue' not available, using custom tool")
                use_mcp = False
        
        if not use_mcp and not self.jira_tool:
            error_msg = "Jira tool is not configured. Please check your Jira credentials."
            state["messages"].append(AIMessage(content=error_msg))
            return state
        
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        conversation_history = state.get("conversation_history", [])
        
        # Gather context
        context_str = self._format_messages_for_context(messages[-6:])
        if conversation_history:
            context_str += "\n\nConversation History:\n"
            for msg in conversation_history[-5:]:
                context_str += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
        
        # Generate Jira backlog details using LLM
        generation_prompt = f"""
        Based on the conversation context below, create a comprehensive Jira backlog item.
        
        CONTEXT:
        {context_str}
        
        User request: {user_input}
        
        REQUIREMENTS:
        1. Summary: Concise title
        2. Business Value: Why this is important
        3. Acceptance Criteria: List of verifiable criteria
        4. Priority: High, Medium, or Low (infer from context, default to Medium)
        5. INVEST Analysis: Brief check against INVEST principles
        
        OUTPUT FORMAT (JSON):
        {{
            "summary": "...",
            "business_value": "...",
            "acceptance_criteria": ["...", "..."],
            "priority": "...",
            "invest_analysis": "...",
            "description": "..."
        }}
        
        The 'description' field should combine Business Value, AC, and INVEST analysis.
        """
        
        try:
            # Use LLM to generate backlog data with timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.llm.invoke,
                    [
                        SystemMessage(content="You are a Jira Product Owner assistant. Always respond with valid JSON."),
                        HumanMessage(content=generation_prompt)
                    ]
                )
                try:
                    response = future.result(timeout=60.0)  # 60 second timeout for backlog generation
                except concurrent.futures.TimeoutError:
                    error_msg = "LLM request timed out while generating Jira backlog. Please try again."
                    state["messages"].append(AIMessage(content=error_msg))
                    return state
            
            # Parse JSON from response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            backlog_data = json.loads(content)
            
            # Track which tool will be used
            tool_used = "Custom Tool"  # Default to custom tool
            result = None  # Initialize result variable
            
            # Create Jira issue using MCP tool if available, otherwise use custom tool
            if use_mcp and mcp_jira_tool:
                tool_used = "MCP Tool"
                print("🚀 Creating Jira issue via MCP tool...")
                print(f"   Summary: {backlog_data.get('summary', 'Untitled Issue')[:50]}...")
                print(f"   Priority: {backlog_data.get('priority', 'Medium')}")
                
                try:
                    # Call MCP tool with additional timeout wrapper for safety
                    import time
                    start_time = time.time()
                    
                    # Call MCP tool using synchronous invoke method with timeout
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            mcp_jira_tool.invoke,
                            {
                                'summary': backlog_data.get('summary', 'Untitled Issue'),
                                'description': backlog_data.get('description', ''),
                                'priority': backlog_data.get('priority', 'Medium'),
                                'issue_type': backlog_data.get('issue_type', 'Story')
                            }
                        )
                        try:
                            mcp_result = future.result(timeout=75.0)  # 75 second timeout (MCP has 60s internal, add buffer)
                            elapsed = time.time() - start_time
                            print(f"   MCP tool call completed in {elapsed:.2f}s")
                        except concurrent.futures.TimeoutError:
                            elapsed = time.time() - start_time
                            print(f"⚠ MCP tool call timed out after {elapsed:.2f}s")
                            print("   Falling back to custom tool")
                            tool_used = "Custom Tool (MCP timeout fallback)"
                            result = self.jira_tool.create_issue(
                                summary=backlog_data.get('summary', 'Untitled Issue'),
                                description=backlog_data.get('description', ''),
                                priority=backlog_data.get('priority', 'Medium')
                            )
                            if result.get('success'):
                                print(f"✅ Created issue {result.get('key', 'N/A')} via custom tool (MCP timeout)")
                            else:
                                result = {'success': False, 'error': 'MCP tool timed out and custom tool also failed'}
                            # Skip JSON parsing, use the result directly
                            mcp_result = None
                    
                    if mcp_result is not None:
                        # Parse MCP result (should be JSON string from MCP server)
                        try:
                            mcp_data = None
                            
                            # Check if result is an error message first
                            if isinstance(mcp_result, str):
                                # Check for timeout or error messages
                                if 'timed out' in mcp_result.lower() or 'timeout' in mcp_result.lower():
                                    print(f"⚠ MCP tool returned timeout error: {mcp_result}")
                                    raise Exception(f"MCP tool timeout: {mcp_result}")
                                if mcp_result.strip().startswith('Error:'):
                                    error_msg = mcp_result.replace('Error:', '').strip()
                                    print(f"⚠ MCP tool returned error: {error_msg}")
                                    raise Exception(f"MCP tool error: {error_msg}")
                                
                                # Try to parse as JSON
                                cleaned_result = mcp_result.strip()
                                if cleaned_result.startswith('```'):
                                    # Extract JSON from code block
                                    lines = cleaned_result.split('\n')
                                    json_lines = [line for line in lines if not line.strip().startswith('```')]
                                    cleaned_result = '\n'.join(json_lines)
                                mcp_data = json.loads(cleaned_result)
                            elif isinstance(mcp_result, dict):
                                # Already a dict
                                mcp_data = mcp_result
                            else:
                                # Try to convert to string first, then parse
                                str_result = str(mcp_result)
                                if str_result.startswith('```'):
                                    lines = str_result.split('\n')
                                    json_lines = [line for line in lines if not line.strip().startswith('```')]
                                    str_result = '\n'.join(json_lines)
                                mcp_data = json.loads(str_result)
                            
                            if mcp_data and mcp_data.get('success'):
                                result = {
                                    'success': True,
                                    'key': mcp_data.get('ticket_id') or mcp_data.get('issue_key'),
                                    'link': mcp_data.get('link', f"{Config.JIRA_URL}/browse/{mcp_data.get('ticket_id', '')}"),
                                    'created_by': mcp_data.get('created_by', 'MCP_SERVER'),
                                    'tool_used': mcp_data.get('tool_used', 'custom-jira-mcp-server')
                                }
                                print(f"✅ Created issue {result['key']} via MCP tool")
                            else:
                                error_msg = mcp_data.get('error', 'Unknown error') if mcp_data else 'Invalid response'
                                print(f"❌ MCP Tool failed: {error_msg}")
                                # Fall back to custom tool
                                tool_used = "Custom Tool (MCP error fallback)"
                                result = self.jira_tool.create_issue(
                                    summary=backlog_data.get('summary', 'Untitled Issue'),
                                    description=backlog_data.get('description', ''),
                                    priority=backlog_data.get('priority', 'Medium')
                                )
                        except json.JSONDecodeError as e:
                            # If not JSON, check if it's an error message
                            if isinstance(mcp_result, str) and ('error' in mcp_result.lower() or 'timeout' in mcp_result.lower()):
                                print(f"⚠ MCP Tool returned error message: {mcp_result[:200]}")
                                # Fall back to custom tool
                                tool_used = "Custom Tool (MCP parse error fallback)"
                                result = self.jira_tool.create_issue(
                                    summary=backlog_data.get('summary', 'Untitled Issue'),
                                    description=backlog_data.get('description', ''),
                                    priority=backlog_data.get('priority', 'Medium')
                                )
                            else:
                                print(f"❌ MCP Tool failed: Invalid response format")
                                result = {'success': False, 'error': f'Invalid response format: {str(mcp_result)[:200]}'}
                except Exception as e:
                    error_str = str(e).lower()
                    if 'timeout' in error_str or 'timed out' in error_str:
                        print(f"⚠ MCP tool call timed out: {e}")
                        print("   Falling back to custom tool")
                    else:
                        print(f"❌ MCP tool call failed: {e}")
                        print("   Falling back to custom tool")
                        import traceback
                        traceback.print_exc()
                    
                    # Fall back to custom tool if result is None or failed
                    if result is None or not result.get('success'):
                        tool_used = "Custom Tool (MCP fallback)"
                        try:
                            result = self.jira_tool.create_issue(
                                summary=backlog_data.get('summary', 'Untitled Issue'),
                                description=backlog_data.get('description', ''),
                                priority=backlog_data.get('priority', 'Medium')
                            )
                            if result.get('success'):
                                print(f"✅ Created issue {result.get('key', 'N/A')} via custom tool (fallback)")
                        except Exception as fallback_error:
                            print(f"❌ Custom tool also failed: {fallback_error}")
                            result = {'success': False, 'error': f'MCP tool failed: {str(e)}. Custom tool also failed: {str(fallback_error)}'}
            else:
                # Use custom tool
                print("\n🔧 Using Custom JiraTool to create Jira issue...")
                print(f"   Summary: {backlog_data.get('summary', 'Untitled Issue')[:50]}...")
                print(f"   Priority: {backlog_data.get('priority', 'Medium')}")
                result = self.jira_tool.create_issue(
                    summary=backlog_data.get('summary', 'Untitled Issue'),
                    description=backlog_data.get('description', ''),
                    priority=backlog_data.get('priority', 'Medium')
                )
                if result.get('success'):
                    print(f"✅ Custom Tool SUCCESS: Created issue {result.get('key', 'N/A')}")
                else:
                    print(f"❌ Custom Tool FAILED: {result.get('error', 'Unknown error')}")
            
            print("=" * 70)
            
            # Ensure result is set
            if result is None:
                result = {'success': False, 'error': 'No result from Jira creation attempt'}
            
            if result and result.get('success'):
                state["jira_result"] = {
                    "success": True,
                    "key": result['key'],
                    "link": result['link'],
                    "backlog_data": backlog_data,
                    "tool_used": tool_used  # Store which tool was used
                }
                state["messages"].append(AIMessage(
                    content=f"✅ Successfully created Jira issue: **{result['key']}**\n"
                           f"Link: {result['link']}\n\n"
                           f"_(Created using {tool_used})_"
                ))
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                state["jira_result"] = {"success": False, "error": error_msg}
                
                # Provide user-friendly error message
                if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                    user_message = (
                        f"❌ **Jira Creation Timeout**\n\n"
                        f"The request to create a Jira issue timed out. This could be due to:\n"
                        f"- Network connectivity issues\n"
                        f"- Jira server being slow or temporarily unavailable\n"
                        f"- MCP server taking too long to respond\n\n"
                        f"**What happened:**\n"
                        f"- Attempted to use MCP protocol first\n"
                        f"- Request timed out after 60+ seconds\n"
                        f"- Attempted fallback to direct API\n\n"
                        f"**Please try:**\n"
                        f"- Check your network connection\n"
                        f"- Verify Jira server is accessible\n"
                        f"- Try again in a few moments"
                    )
                else:
                    user_message = f"❌ **Failed to create Jira issue**\n\nError: {error_msg}\n\nPlease check your Jira configuration and try again."
                
                state["messages"].append(AIMessage(content=user_message))
        except Exception as e:
            error_msg = f"Error creating Jira issue: {str(e)}"
            state["jira_result"] = {"success": False, "error": error_msg}
            
            # Provide user-friendly error message
            error_str = str(e).lower()
            if 'timeout' in error_str or 'timed out' in error_str:
                user_message = (
                    f"❌ **Jira Creation Timeout**\n\n"
                    f"The request timed out while creating the Jira issue. "
                    f"Please check your network connection and Jira server status, then try again."
                )
            else:
                user_message = f"❌ **Error creating Jira issue**\n\n{error_msg}\n\nPlease check your configuration and try again."
            
            state["messages"].append(AIMessage(content=user_message))
            import traceback
            traceback.print_exc()
        
        return state
    
    def _handle_evaluation(self, state: AgentState) -> AgentState:
        """Evaluate the created Jira issue."""
        jira_result = state.get("jira_result")
        
        if not jira_result or not jira_result.get("success") or not self.jira_evaluator:
            return state
        
        issue_key = jira_result["key"]
        
        try:
            # Fetch the issue from Jira
            issue = self.jira_evaluator.jira.issue(issue_key)
            issue_dict = {
                'key': issue.key,
                'summary': issue.fields.summary,
                'description': issue.fields.description or '',
                'status': issue.fields.status.name,
                'priority': issue.fields.priority.name if issue.fields.priority else 'Unassigned'
            }
            
            # Evaluate maturity
            evaluation = self.jira_evaluator.evaluate_maturity(issue_dict)
            
            if 'error' not in evaluation:
                state["evaluation_result"] = evaluation
                
                # Format evaluation message
                eval_msg = (
                    f"📊 **Maturity Evaluation Results:**\n"
                    f"Overall Score: **{evaluation['overall_maturity_score']}/100**\n\n"
                )
                
                if evaluation.get('strengths'):
                    eval_msg += "**Strengths:**\n"
                    for strength in evaluation['strengths']:
                        eval_msg += f"  ✓ {strength}\n"
                    eval_msg += "\n"
                
                if evaluation.get('recommendations'):
                    eval_msg += "**Recommendations:**\n"
                    for rec in evaluation['recommendations']:
                        eval_msg += f"  → {rec}\n"
                
                state["messages"].append(AIMessage(content=eval_msg))
            else:
                state["evaluation_result"] = {"error": evaluation.get('error')}
        except Exception as e:
            state["evaluation_result"] = {"error": str(e)}
            print(f"Error during evaluation: {e}")
        
        return state
    
    def _route_after_evaluation(self, state: AgentState) -> str:
        """Route after evaluation - decide if we should create Confluence page."""
        # Create Confluence page if tool is available and Jira was created successfully
        # Even if evaluation failed, we can still create the page with basic info
        # Check for both custom tool and MCP tool
        has_confluence_capability = (
            self.confluence_tool or 
            (self.use_mcp and self.mcp_integration is not None)
        )
        
        if has_confluence_capability and state.get("jira_result", {}).get("success"):
            return "confluence_creation"
        return "end"
    
    def _handle_confluence_creation(self, state: AgentState) -> AgentState:
        """Create Confluence page for the Jira issue using MCP protocol with fallback."""
        jira_result = state.get("jira_result", {})
        evaluation_result = state.get("evaluation_result", {})
        backlog_data = jira_result.get("backlog_data", {})
        
        if not jira_result.get("success"):
            state["messages"].append(AIMessage(
                content="⚠ Cannot create Confluence page: Jira issue was not created successfully."
            ))
            return state
        
        issue_key = jira_result["key"]
        
        try:
            print(f"Creating Confluence page for {issue_key}...")
            
            # Format Confluence content
            confluence_content = self._format_confluence_content(
                issue_key=issue_key,
                backlog_data=backlog_data,
                evaluation=evaluation_result if evaluation_result else {},
                jira_link=jira_result["link"]
            )
            
            page_title = f"{issue_key}: {backlog_data.get('summary', 'Untitled')}"
            
            # Try MCP protocol first if enabled
            use_mcp = self.use_mcp and self.mcp_integration is not None
            confluence_result = None
            tool_used = None
            
            if use_mcp:
                # Initialize MCP if needed (with timeout to prevent blocking)
                if not self.mcp_integration._initialized:
                    print("🔄 Initializing MCP integration for Confluence...")
                    try:
                        import asyncio
                        import concurrent.futures
                        # Initialize with timeout to prevent blocking
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.mcp_integration.initialize())
                            try:
                                future.result(timeout=15.0)  # 15 second timeout for initialization
                                print("✓ MCP integration initialized for Confluence")
                            except concurrent.futures.TimeoutError:
                                print(f"⚠ MCP initialization timeout (15s) for Confluence")
                                use_mcp = False
                    except Exception as e:
                        print(f"⚠ MCP initialization failed: {e}")
                        use_mcp = False
                
                # Try to get MCP Confluence tool
                if use_mcp:
                    # Only get tools if MCP is initialized (don't trigger initialization here)
                    if self.mcp_integration._initialized:
                        all_tools = self.mcp_integration.get_tools()
                        print(f"🔍 [MCP PROTOCOL] Available MCP tools: {[tool.name for tool in all_tools]}")
                    else:
                        print(f"🔍 [MCP PROTOCOL] MCP not initialized yet, skipping tool discovery")
                        all_tools = []
                    
                    # Look for Confluence tools - check both exact names and patterns
                    mcp_confluence_tool = None
                    confluence_tool_candidates = []
                    
                    # Common MCP tool names for Confluence page creation (including Rovo server names)
                    tool_name_patterns = [
                        'create_confluence_page', 'confluence_create_page', 
                        'create_page', 'confluence_page_create',
                        'confluence_create', 'create_confluence',
                        'atlassian_confluence_create_page', 'atlassian_create_page',
                        'rovo_create_page', 'rovo_confluence_create'
                    ]
                    
                    # First try exact name matches
                    for tool_name in tool_name_patterns:
                        tool = self.mcp_integration.get_tool(tool_name)
                        if tool:
                            confluence_tool_candidates.append((tool_name, tool))
                            print(f"  ✓ Found potential Confluence tool: {tool_name}")
                    
                    # If no exact match, search through all tools for Confluence-related ones
                    if not confluence_tool_candidates:
                        for tool in all_tools:
                            tool_name_lower = tool.name.lower()
                            # Check if tool name contains confluence/page/create keywords
                            if any(keyword in tool_name_lower for keyword in 
                                  ['confluence', 'page', 'create', 'rovo']):
                                if 'create' in tool_name_lower or 'page' in tool_name_lower:
                                    confluence_tool_candidates.append((tool.name, tool))
                                    print(f"  ✓ Found potential Confluence tool by pattern: {tool.name}")
                    
                    # Use the first candidate found
                    if confluence_tool_candidates:
                        tool_name, mcp_confluence_tool = confluence_tool_candidates[0]
                        print(f"✓ Selected MCP Confluence tool: {tool_name}")
                    
                    if mcp_confluence_tool:
                        print(f"🚀 [MCP PROTOCOL] Creating Confluence page via MCP tool...")
                        print(f"   MCP Tool: {mcp_confluence_tool.name}")
                        print(f"   Title: {page_title}")
                        tool_used = "MCP Protocol"
                        
                        try:
                            # Call MCP tool with timeout
                            import asyncio
                            import concurrent.futures
                            
                            # Prepare arguments for MCP tool
                            # Try different parameter name variations based on common MCP server patterns
                            # Rovo server might use different parameter names
                            mcp_args = {
                                'title': page_title,
                                'content': confluence_content,
                                'space_key': Config.CONFLUENCE_SPACE_KEY,
                                'spaceKey': Config.CONFLUENCE_SPACE_KEY,  # camelCase variant
                                'space': Config.CONFLUENCE_SPACE_KEY,
                                'body': confluence_content,  # Some servers use 'body' instead of 'content'
                                'html': confluence_content,  # Some servers expect HTML
                                'text': confluence_content  # Some servers expect plain text
                            }
                            
                            # Log the tool being used and arguments
                            print(f"   Tool Name: {mcp_confluence_tool.name}")
                            print(f"   Arguments: title='{page_title[:50]}...', space_key='{Config.CONFLUENCE_SPACE_KEY}'")
                            
                            # Try calling MCP tool with timeout
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(mcp_confluence_tool.invoke, mcp_args)
                                try:
                                    mcp_result = future.result(timeout=30.0)  # 30 second timeout
                                    
                                    # Parse MCP result
                                    if isinstance(mcp_result, str):
                                        # Try to parse as JSON
                                        import json
                                        try:
                                            if mcp_result.strip().startswith('```'):
                                                # Extract JSON from code block
                                                lines = mcp_result.split('\n')
                                                json_lines = [line for line in lines 
                                                             if not line.strip().startswith('```')]
                                                mcp_result = '\n'.join(json_lines)
                                            mcp_data = json.loads(mcp_result)
                                        except json.JSONDecodeError:
                                            # If not JSON, check if it contains success indicators
                                            if 'success' in mcp_result.lower() or 'created' in mcp_result.lower():
                                                # Extract page ID and link if possible
                                                confluence_result = {
                                                    'success': True,
                                                    'title': page_title,
                                                    'link': f"{Config.CONFLUENCE_URL}/pages/viewpage.action?pageId=unknown",
                                                    'tool_used': 'MCP Protocol'
                                                }
                                            else:
                                                raise Exception(f"MCP tool returned unexpected format: {mcp_result[:200]}")
                                    elif isinstance(mcp_result, dict):
                                        mcp_data = mcp_result
                                    else:
                                        mcp_data = {'success': False, 'error': f'Unexpected result type: {type(mcp_result)}'}
                                    
                                    if isinstance(mcp_data, dict):
                                        if mcp_data.get('success'):
                                            confluence_result = {
                                                'success': True,
                                                'id': mcp_data.get('id') or mcp_data.get('page_id'),
                                                'title': mcp_data.get('title', page_title),
                                                'link': mcp_data.get('link') or 
                                                       f"{Config.CONFLUENCE_URL}/pages/viewpage.action?pageId={mcp_data.get('id', 'unknown')}",
                                                'tool_used': 'MCP Protocol'
                                            }
                                            print(f"✅ [MCP PROTOCOL] Confluence page created successfully")
                                        else:
                                            raise Exception(mcp_data.get('error', 'Unknown MCP error'))
                                    
                                except concurrent.futures.TimeoutError:
                                    print(f"⚠ [MCP PROTOCOL] Timeout after 30 seconds, falling back to direct API")
                                    tool_used = None  # Will trigger fallback
                                    raise asyncio.TimeoutError("MCP tool call timeout")
                                    
                        except (asyncio.TimeoutError, Exception) as e:
                            print(f"⚠ [MCP PROTOCOL] Failed: {str(e)}")
                            print(f"   Falling back to direct Confluence API call")
                            tool_used = None  # Will trigger fallback
                            use_mcp = False
            
            # Fallback to direct API if MCP failed or not available
            if not confluence_result and self.confluence_tool:
                if use_mcp:
                    print(f"⚠ [MCP PROTOCOL] MCP tool not found or failed, falling back to direct API")
                    if self.mcp_integration and self.mcp_integration._initialized:
                        available_tools = [tool.name for tool in self.mcp_integration.get_tools()]
                        print(f"   Available MCP tools: {available_tools}")
                        if not available_tools:
                            print(f"   ⚠ No MCP tools available - MCP integration may not be properly initialized")
                else:
                    print(f"⚠ [MCP PROTOCOL] MCP not enabled, using direct API")
                print(f"🔧 [DIRECT API] Creating Confluence page via direct API call...")
                tool_used = "Direct API"
                confluence_result = self.confluence_tool.create_page(
                    title=page_title,
                    content=confluence_content
                )
                if confluence_result.get('success'):
                    confluence_result['tool_used'] = 'Direct API'
            
            # Handle result
            if confluence_result and confluence_result.get('success'):
                state["confluence_result"] = confluence_result
                tool_info = f" (via {tool_used})" if tool_used else ""
                state["messages"].append(AIMessage(
                    content=f"📄 **Confluence Page Created{tool_info}:**\n"
                           f"Title: {confluence_result['title']}\n"
                           f"Link: {confluence_result['link']}"
                ))
                print(f"✓ Confluence page created: {confluence_result['link']}")
            else:
                error_msg = confluence_result.get('error', 'Unknown error') if confluence_result else 'No tool available'
                user_friendly_msg = (
                    f"⚠ **Confluence page creation failed:**\n"
                    f"The system attempted to create the page but encountered an issue.\n"
                    f"Error: {error_msg}\n\n"
                    f"**What happened:**\n"
                    f"- Tried to use MCP protocol first\n"
                    f"- Fell back to direct API call\n"
                    f"- Both methods encountered issues\n\n"
                    f"**Please check:**\n"
                    f"- CONFLUENCE_URL and CONFLUENCE_SPACE_KEY in .env file\n"
                    f"- API token has Confluence write permissions\n"
                    f"- Network connectivity to Confluence\n"
                )
                state["messages"].append(AIMessage(content=user_friendly_msg))
                print(f"✗ Confluence page creation failed: {error_msg}")
                
        except Exception as e:
            error_detail = (
                f"⚠ **Confluence page creation failed:**\n"
                f"Exception: {str(e)}\n\n"
                f"The system tried both MCP protocol and direct API methods.\n"
                f"Please check your Confluence configuration and network connectivity."
            )
            state["messages"].append(AIMessage(content=error_detail))
            print(f"Error creating Confluence page: {e}")
            import traceback
            traceback.print_exc()
        
        return state
    
    def _handle_rag_query(self, state: AgentState) -> AgentState:
        """Handle RAG query - retrieve relevant context and answer."""
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        
        # Try to get RAG service from state or initialize
        rag_service = getattr(self, '_rag_service', None)
        
        if rag_service:
            try:
                # Retrieve relevant context using RAG service with timeout
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(rag_service.get_context, user_input, 3)
                    try:
                        context_str = future.result(timeout=15.0)  # 15 second timeout for RAG retrieval
                    except concurrent.futures.TimeoutError:
                        print("⚠ RAG retrieval timeout (15s), proceeding without context")
                        context_str = None
                
                if context_str and context_str.strip():
                    # Add context to prompt
                    rag_prompt = f"""
                    {context_str}
                    
                    User Question: {user_input}
                    
                    Please answer the user's question using the provided context. 
                    If the context doesn't contain enough information, say so and provide 
                    a general answer based on your knowledge.
                    """
                    
                    # Store raw chunks for reference
                    chunks = rag_service.retrieve(user_input, top_k=3)
                    state["rag_context"] = [chunk.get('content', '') for chunk in chunks]
                    messages.append(HumanMessage(content=rag_prompt))
                else:
                    # No relevant context found, proceed with normal chat
                    messages.append(HumanMessage(content=user_input))
            except Exception as e:
                print(f"Error in RAG retrieval: {e}")
                messages.append(HumanMessage(content=user_input))
        else:
            # No RAG service available, proceed with normal chat
            messages.append(HumanMessage(content=user_input))
        
        # Generate response
        try:
            if not messages or not isinstance(messages[0], SystemMessage):
                system_msg = SystemMessage(
                    content="You are a helpful AI assistant. Use the provided context to answer questions accurately."
                )
                messages = [system_msg] + messages
            
            response = self.llm.invoke(messages)
            messages.append(response)
            state["messages"] = messages
        except Exception as e:
            error_msg = AIMessage(content=f"I apologize, but I encountered an error: {str(e)}")
            messages.append(error_msg)
            state["messages"] = messages
        
        return state
    
    def _format_messages_for_context(self, messages: List[BaseMessage]) -> str:
        """Format messages for context string."""
        context = ""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                context += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                context += f"Assistant: {msg.content}\n"
        return context
    
    def _format_confluence_content(self, issue_key: str, backlog_data: Dict, 
                                   evaluation: Dict, jira_link: str) -> str:
        """Format content for Confluence page in HTML format."""
        # Build HTML content
        html_parts = []
        
        # Title and Jira link
        html_parts.append(f"<h1>{issue_key}: {backlog_data.get('summary', 'Untitled')}</h1>")
        html_parts.append(f"<p><strong>Jira Link:</strong> <a href=\"{jira_link}\">{jira_link}</a></p>")
        
        # Priority
        priority = backlog_data.get('priority', 'Not specified')
        html_parts.append(f"<p><strong>Priority:</strong> {priority}</p>")
        
        # Business Value
        business_value = backlog_data.get('business_value', 'N/A')
        html_parts.append("<h2>Business Value</h2>")
        html_parts.append(f"<p>{business_value}</p>")
        
        # Acceptance Criteria
        acceptance_criteria = backlog_data.get('acceptance_criteria', [])
        if acceptance_criteria:
            html_parts.append("<h2>Acceptance Criteria</h2>")
            html_parts.append("<ul>")
            for ac in acceptance_criteria:
                html_parts.append(f"<li>{ac}</li>")
            html_parts.append("</ul>")
        
        # INVEST Analysis
        invest_analysis = backlog_data.get('invest_analysis', '')
        if invest_analysis:
            html_parts.append("<h2>INVEST Analysis</h2>")
            html_parts.append(f"<p>{invest_analysis}</p>")
        
        # Maturity Evaluation (if available)
        if evaluation and 'overall_maturity_score' in evaluation:
            html_parts.append("<h2>Maturity Evaluation</h2>")
            html_parts.append(f"<p><strong>Overall Score:</strong> {evaluation['overall_maturity_score']}/100</p>")
            
            # Strengths
            if evaluation.get('strengths'):
                html_parts.append("<h3>Strengths</h3>")
                html_parts.append("<ul>")
                for strength in evaluation['strengths']:
                    html_parts.append(f"<li>{strength}</li>")
                html_parts.append("</ul>")
            
            # Weaknesses
            if evaluation.get('weaknesses'):
                html_parts.append("<h3>Areas for Improvement</h3>")
                html_parts.append("<ul>")
                for weakness in evaluation['weaknesses']:
                    html_parts.append(f"<li>{weakness}</li>")
                html_parts.append("</ul>")
            
            # Recommendations
            if evaluation.get('recommendations'):
                html_parts.append("<h3>Recommendations</h3>")
                html_parts.append("<ul>")
                for rec in evaluation['recommendations']:
                    html_parts.append(f"<li>{rec}</li>")
                html_parts.append("</ul>")
            
            # Detailed Scores
            if evaluation.get('detailed_scores'):
                html_parts.append("<h3>Detailed Scores</h3>")
                html_parts.append("<ul>")
                for criterion, score in evaluation['detailed_scores'].items():
                    criterion_name = criterion.replace('_', ' ').title()
                    html_parts.append(f"<li><strong>{criterion_name}:</strong> {score}/100</li>")
                html_parts.append("</ul>")
        
        return "\n".join(html_parts)
    
    def invoke(self, user_input: str, conversation_history: Optional[List[Dict]] = None) -> str:
        """
        Invoke the agent with user input.
        
        Args:
            user_input: User's message
            conversation_history: Previous conversation messages
            
        Returns:
            Agent's response as string
        """
        # Initialize state
        initial_state: AgentState = {
            "messages": [],
            "user_input": user_input,
            "intent": None,
            "jira_result": None,
            "evaluation_result": None,
            "confluence_result": None,
            "rag_context": None,
            "conversation_history": conversation_history or [],
            "next_action": None
        }
        
        # Add conversation history to messages
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    initial_state["messages"].append(HumanMessage(content=content))
                elif role == 'assistant':
                    initial_state["messages"].append(AIMessage(content=content))
        
        # Run the graph (LangGraph execution)
        print(f"🔄 LangGraph: Processing input through agent graph...")
        final_state = self.graph.invoke(initial_state)
        
        # Log the intent that was detected
        detected_intent = final_state.get("intent", "unknown")
        print(f"✓ LangGraph: Intent detected = '{detected_intent}'")
        
        # Log which nodes were executed
        if detected_intent == "jira_creation":
            print(f"  → Executed nodes: intent_detection → jira_creation → evaluation")
            if final_state.get("jira_result", {}).get("success"):
                print(f"  → Jira issue created: {final_state.get('jira_result', {}).get('key', 'N/A')}")
        elif detected_intent == "rag_query":
            print(f"  → Executed nodes: intent_detection → rag_query")
        elif detected_intent == "general_chat":
            print(f"  → Executed nodes: intent_detection → general_chat")
        
        # Extract the last assistant message
        messages = final_state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage):
                print(f"✓ LangGraph: Response generated successfully")
                return last_msg.content
        
        return "I apologize, but I couldn't generate a response."

