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
        
        # MCP integration disabled
        self.mcp_integration = None
        self.use_mcp = False
        
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
        jira_creation_keywords = ['create jira', 'create issue', 'create ticket', 'create backlog', 
                                  'new jira', 'new issue', 'new ticket', 'add jira', 'add issue',
                                  'make jira', 'make issue', 'make ticket']
        
        # Expanded RAG keywords for knowledge/documentation queries
        rag_keywords = ['what is', 'what are', 'how to', 'how do', 'explain', 'tell me about',
                       'document', 'documentation', 'guide', 'help with', 'information about',
                       'describe', 'definition', 'meaning', 'example']
        
        # General chat keywords (simple questions, greetings)
        general_chat_keywords = ['hello', 'hi', 'hey', 'who are you', 'what are you',
                                'how are you', 'thanks', 'thank you', 'bye', 'goodbye',
                                'help', 'assist', 'chat', 'talk']
        
        # Check for Jira creation intent keywords
        if any(keyword in user_input for keyword in jira_creation_keywords):
            if self.jira_tool:
                state["intent"] = "jira_creation"
                print(f"  → Intent: jira_creation (keyword match)")
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
        
        # Only route to jira_creation if we have tools available
        # MCP disabled - only use custom tools
        if intent == "jira_creation" and self.jira_tool:
            return "jira_creation"
        elif intent == "rag_query":
            return "rag_query"
        else:
            return "general_chat"
    
    def _handle_general_chat(self, state: AgentState) -> AgentState:
        """Handle general conversation."""
        messages = state.get("messages", [])
        user_input = state.get("user_input", "")
        
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
                    error_msg = AIMessage(content="I apologize, but the request timed out. Please check your OpenAI API key and network connection. The API may be slow or unavailable.")
                    messages.append(error_msg)
                    state["messages"] = messages
        except Exception as e:
            print(f"⚠ LLM call error: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            error_msg = AIMessage(content=f"I apologize, but I encountered an error: {str(e)}. Please check your API key and network connection.")
            messages.append(error_msg)
            state["messages"] = messages
        
        return state
    
    def _handle_jira_creation(self, state: AgentState) -> AgentState:
        """Handle Jira issue creation."""
        # MCP disabled - only use custom tools
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
            
            # Create Jira issue using custom tool (MCP disabled)
            result = self.jira_tool.create_issue(
                summary=backlog_data.get('summary', 'Untitled Issue'),
                description=backlog_data.get('description', ''),
                priority=backlog_data.get('priority', 'Medium')
            )
            
            if result.get('success'):
                state["jira_result"] = {
                    "success": True,
                    "key": result['key'],
                    "link": result['link'],
                    "backlog_data": backlog_data
                }
                state["messages"].append(AIMessage(
                    content=f"✅ Successfully created Jira issue: **{result['key']}**\nLink: {result['link']}"
                ))
            else:
                state["jira_result"] = {"success": False, "error": result.get('error')}
                state["messages"].append(AIMessage(
                    content=f"❌ Failed to create Jira issue: {result.get('error', 'Unknown error')}"
                ))
        except Exception as e:
            error_msg = f"Error creating Jira issue: {str(e)}"
            state["jira_result"] = {"success": False, "error": error_msg}
            state["messages"].append(AIMessage(content=f"❌ {error_msg}"))
        
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
        if self.confluence_tool and state.get("jira_result", {}).get("success"):
            return "confluence_creation"
        return "end"
    
    def _handle_confluence_creation(self, state: AgentState) -> AgentState:
        """Create Confluence page for the Jira issue."""
        if not self.confluence_tool:
            state["messages"].append(AIMessage(
                content="⚠ Confluence tool is not configured. Skipping page creation."
            ))
            return state
        
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
            
            # Create page
            confluence_result = self.confluence_tool.create_page(
                title=f"{issue_key}: {backlog_data.get('summary', 'Untitled')}",
                content=confluence_content
            )
            
            if confluence_result.get('success'):
                state["confluence_result"] = confluence_result
                state["messages"].append(AIMessage(
                    content=f"📄 **Confluence Page Created:**\n"
                           f"Title: {confluence_result['title']}\n"
                           f"Link: {confluence_result['link']}"
                ))
                print(f"✓ Confluence page created: {confluence_result['link']}")
            else:
                error_msg = confluence_result.get('error', 'Unknown error')
                detailed_error = f"⚠ **Confluence page creation failed:**\n"
                detailed_error += f"Error: {error_msg}\n\n"
                detailed_error += "**Possible causes:**\n"
                detailed_error += "- CONFLUENCE_URL not configured correctly\n"
                detailed_error += "- CONFLUENCE_SPACE_KEY not set or invalid\n"
                detailed_error += "- Insufficient permissions for Confluence API\n"
                detailed_error += "- Network connectivity issues\n\n"
                detailed_error += "**To fix:**\n"
                detailed_error += "1. Check your .env file has CONFLUENCE_URL and CONFLUENCE_SPACE_KEY\n"
                detailed_error += "2. Verify your API token has Confluence write permissions\n"
                detailed_error += "3. Ensure the space key exists and you have access\n"
                detailed_error += "See CONFLUENCE_SETUP.md for details."
                
                state["messages"].append(AIMessage(content=detailed_error))
                print(f"✗ Confluence page creation failed: {error_msg}")
        except Exception as e:
            error_detail = f"⚠ **Confluence page creation failed:**\n"
            error_detail += f"Exception: {str(e)}\n\n"
            error_detail += "Please check:\n"
            error_detail += "- Confluence configuration in .env file\n"
            error_detail += "- Network connectivity\n"
            error_detail += "- API credentials"
            
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

