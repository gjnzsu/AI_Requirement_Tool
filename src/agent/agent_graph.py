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
                 use_mcp: bool = True):
        """
        Initialize the LangGraph agent.
        
        Args:
            provider_name: LLM provider ('openai' or 'gemini')
            model: Model name (if None, uses default from Config)
            temperature: Sampling temperature
            enable_tools: Whether to enable Jira/Confluence tools
            rag_service: Optional RAG service instance
            use_mcp: Whether to use MCP protocol for tools (default: True)
        """
        self.provider_name = provider_name.lower()
        self.temperature = temperature
        self.enable_tools = enable_tools
        self.use_mcp = use_mcp
        self._rag_service = rag_service
        
        # Initialize LLM
        self.llm = self._initialize_llm(model)
        
        # Initialize MCP integration
        self.mcp_integration = None
        if self.use_mcp:
            try:
                self.mcp_integration = MCPIntegration(use_mcp=True)
                # Initialize MCP asynchronously
                import asyncio
                try:
                    asyncio.run(self.mcp_integration.initialize())
                    # If MCP failed to initialize, disable it
                    if not self.mcp_integration._initialized:
                        self.use_mcp = False
                except Exception as e:
                    print(f"⚠ MCP initialization failed: {e}")
                    print("   Falling back to custom tools")
                    self.use_mcp = False
            except Exception as e:
                print(f"⚠ MCP not available: {e}")
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
            return ChatOpenAI(
                model=model_name,
                temperature=self.temperature,
                api_key=api_key
            )
        elif self.provider_name == "gemini":
            api_key = Config.GEMINI_API_KEY
            model_name = model or Config.GEMINI_MODEL
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in configuration")
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
        """Detect user intent from the input."""
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        
        # Use LLM to detect intent
        intent_prompt = f"""
        Analyze the user's input and determine their intent. Respond with ONLY one of these options:
        - "jira_creation" if the user wants to create a Jira issue/ticket/backlog
        - "rag_query" if the user is asking a question that might benefit from document retrieval
        - "general_chat" for normal conversation
        
        User input: {user_input}
        
        Recent conversation context:
        {self._format_messages_for_context(messages[-4:]) if messages else "No previous context"}
        
        Respond with ONLY the intent keyword (jira_creation, rag_query, or general_chat):
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=intent_prompt)])
            intent = response.content.strip().lower()
            
            # Validate intent
            if intent not in ["jira_creation", "rag_query", "general_chat"]:
                intent = "general_chat"  # Default fallback
        except Exception as e:
            print(f"Error detecting intent: {e}")
            intent = "general_chat"
        
        state["intent"] = intent
        return state
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Route to appropriate node based on detected intent."""
        intent = state.get("intent", "general_chat")
        
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
        
        # Generate response
        try:
            response = self.llm.invoke(messages)
            messages.append(response)
            state["messages"] = messages
        except Exception as e:
            error_msg = AIMessage(content=f"I apologize, but I encountered an error: {str(e)}")
            messages.append(error_msg)
            state["messages"] = messages
        
        return state
    
    def _handle_jira_creation(self, state: AgentState) -> AgentState:
        """Handle Jira issue creation."""
        # Try MCP tools first, fall back to custom tools
        use_mcp = (self.use_mcp and 
                   self.mcp_integration and 
                   self.mcp_integration._initialized and
                   self.mcp_integration.has_tool('create_issue'))
        
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
            # Use LLM to generate backlog data
            response = self.llm.invoke([
                SystemMessage(content="You are a Jira Product Owner assistant. Always respond with valid JSON."),
                HumanMessage(content=generation_prompt)
            ])
            
            # Parse JSON from response
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            backlog_data = json.loads(content)
            
            # Create Jira issue (use MCP if available, otherwise custom tool)
            if use_mcp:
                try:
                    # Use MCP tool
                    mcp_tool = self.mcp_integration.get_tool('create_issue')
                    if mcp_tool:
                        tool_result = mcp_tool.run(
                            summary=backlog_data.get('summary', 'Untitled Issue'),
                            description=backlog_data.get('description', ''),
                            priority=backlog_data.get('priority', 'Medium')
                        )
                        # Parse MCP result (format may vary)
                        # MCP tools return text, so we need to parse it
                        result = {'success': True, 'key': 'MCP-ISSUE', 'link': tool_result}
                    else:
                        # Fall back to custom tool
                        result = self.jira_tool.create_issue(
                            summary=backlog_data.get('summary', 'Untitled Issue'),
                            description=backlog_data.get('description', ''),
                            priority=backlog_data.get('priority', 'Medium')
                        )
                except Exception as e:
                    print(f"⚠ MCP tool execution failed: {e}")
                    print("   Falling back to custom tool")
                    # Fall back to custom tool
                    result = self.jira_tool.create_issue(
                        summary=backlog_data.get('summary', 'Untitled Issue'),
                        description=backlog_data.get('description', ''),
                        priority=backlog_data.get('priority', 'Medium')
                    )
            else:
                # Use custom tool
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
                # Retrieve relevant context using RAG service
                context_str = rag_service.get_context(user_input, top_k=3)
                
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
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        # Extract the last assistant message
        messages = final_state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage):
                return last_msg.content
        
        return "I apologize, but I couldn't generate a response."

