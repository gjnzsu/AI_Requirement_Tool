"""
Enhanced LLM-powered Chatbot.

This chatbot uses the multi-provider LLM infrastructure to provide
intelligent conversational responses.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Optional
from src.tools.jira_tool import JiraTool
from src.tools.confluence_tool import ConfluenceTool

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm import LLMRouter, LLMProviderManager
from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.services.memory_manager import MemoryManager
from src.services.memory_summarizer import MemorySummarizer
from src.rag import RAGService
from config.config import Config
from src.agent import ChatbotAgent
from src.utils.logger import get_logger

logger = get_logger('chatbot')


class Chatbot:
    """
    Enhanced chatbot using LLM providers for intelligent conversations.
    
    Features:
    - Multi-provider LLM support (OpenAI, Gemini, DeepSeek)
    - Persistent conversation history/memory
    - Automatic fallback to backup providers
    - Configurable system prompts
    - Context window management with summarization
    - RAG (Retrieval-Augmented Generation) support
    """
    
    def __init__(self, 
                 provider_name: Optional[str] = None,
                 use_fallback: bool = True,
                 system_prompt: Optional[str] = None,
                 temperature: float = 0.7,
                 max_history: int = 10,
                 use_persistent_memory: bool = True,
                 conversation_id: Optional[str] = None,
                 memory_db_path: Optional[str] = None,
                 use_rag: bool = True,
                 rag_top_k: int = 3,
                 enable_mcp_tools: bool = True,
                 lazy_load_tools: bool = True,
                 use_agent: bool = True,
                 use_mcp: bool = True):
        """
        Initialize the chatbot.
        
        Args:
            provider_name: LLM provider to use ('openai', 'gemini', 'deepseek').
                          If None, uses Config.LLM_PROVIDER
            use_fallback: Whether to enable automatic fallback to backup providers
            system_prompt: Custom system prompt. If None, uses default
            temperature: Sampling temperature (0.0 to 1.0). Higher = more creative
            max_history: Maximum number of conversation turns to keep in context window
            use_persistent_memory: Whether to use persistent storage for conversations
            conversation_id: Current conversation ID (for persistent memory)
            memory_db_path: Path to memory database (optional)
            use_rag: Whether to enable RAG (Retrieval-Augmented Generation)
            rag_top_k: Number of relevant chunks to retrieve for RAG
            enable_mcp_tools: Whether to enable MCP tools (Jira, Confluence)
            lazy_load_tools: If True, tools are initialized only when needed (recommended)
            use_agent: Whether to use LangGraph agent for intelligent tool orchestration (recommended)
            use_mcp: Whether to use MCP protocol for tools (default: True, falls back to custom tools if MCP unavailable)
        """
        self.provider_name = provider_name or Config.LLM_PROVIDER.lower()
        self.use_fallback = use_fallback
        self.temperature = temperature
        self.max_history = max_history
        self.use_persistent_memory = use_persistent_memory
        self.conversation_id = conversation_id
        self.use_rag = use_rag
        self.rag_top_k = rag_top_k
        self.enable_mcp_tools = enable_mcp_tools
        self.lazy_load_tools = lazy_load_tools
        self.use_agent = use_agent
        self.use_mcp = use_mcp
        self._tools_initialized = False
        self.agent = None  # Will be initialized after RAG service
        
        # Default system prompt
        self.system_prompt = system_prompt or (
            "You are a helpful, friendly, and knowledgeable AI assistant. "
            "You provide clear, concise, and accurate responses. "
            "You are conversational and engaging while being professional."
        )
        
        # Conversation history: list of {"role": "user"/"assistant", "content": "..."}
        # This is kept for backward compatibility and immediate context
        self.conversation_history: List[Dict[str, str]] = []
        
        # Initialize memory manager if persistent memory is enabled
        self.memory_manager = None
        self.memory_summarizer = None
        if self.use_persistent_memory:
            try:
                self.memory_manager = MemoryManager(
                    db_path=memory_db_path,
                    max_context_messages=self.max_history * 2
                )
                logger.info("Initialized Memory Manager")
            except Exception as e:
                logger.warning(f"Failed to initialize Memory Manager: {e}")
                logger.info("Falling back to in-memory storage")
                self.use_persistent_memory = False
        
        # Initialize LLM provider
        self.llm_provider = None
        self.provider_manager = None
        self._initialize_provider()
        
        # Initialize memory summarizer (needs LLM provider)
        if self.use_persistent_memory and self.memory_manager:
            try:
                # Get LLM provider for summarizer
                if self.provider_manager:
                    summarizer_llm = self.provider_manager.primary
                else:
                    summarizer_llm = self.llm_provider
                
                self.memory_summarizer = MemorySummarizer(llm_provider=summarizer_llm)
                logger.info("Initialized Memory Summarizer")
            except Exception as e:
                logger.warning(f"Failed to initialize Memory Summarizer: {e}")
        
        # Initialize RAG service if enabled
        self.rag_service = None
        if self.use_rag:
            try:
                logger.info("=" * 70)
                logger.info("Initializing RAG Service")
                logger.info("=" * 70)
                # Check if OpenAI API key is available (required for embeddings)
                if Config.OPENAI_API_KEY:
                    self.rag_service = RAGService(
                        chunk_size=getattr(Config, 'RAG_CHUNK_SIZE', 1000),
                        chunk_overlap=getattr(Config, 'RAG_CHUNK_OVERLAP', 200),
                        embedding_model=getattr(Config, 'RAG_EMBEDDING_MODEL', 'text-embedding-ada-002'),
                        enable_cache=getattr(Config, 'RAG_ENABLE_CACHE', True),
                        cache_ttl_hours=getattr(Config, 'RAG_CACHE_TTL_HOURS', 24)
                    )
                    cache_status = "with caching" if getattr(Config, 'RAG_ENABLE_CACHE', True) else "without caching"
                    logger.info(f"Initialized RAG Service ({cache_status})")
                    logger.info("=" * 70)
                else:
                    logger.warning("RAG disabled: OPENAI_API_KEY not found (required for embeddings)")
                    logger.info("=" * 70)
                    self.use_rag = False
            except Exception as e:
                logger.warning(f"Failed to initialize RAG Service: {e}")
                logger.info("RAG will be disabled")
                logger.info("=" * 70)
                self.use_rag = False
        else:
            logger.info("=" * 70)
            logger.info("RAG Service")
            logger.info("=" * 70)
            logger.info("RAG is disabled (use_rag=False)")
            logger.info("=" * 70)
        
        # Initialize Tools (lazy loading - only when needed)
        self.jira_tool = None
        self.jira_evaluator = None
        self.confluence_tool = None
        
        # Initialize tools immediately only if lazy loading is disabled
        if self.enable_mcp_tools and not self.lazy_load_tools:
            self._initialize_tools()
        
        # Initialize LangGraph agent if enabled (after RAG service is ready)
        if self.use_agent:
            try:
                # Log MCP status
                logger.info("=" * 70)
                logger.info("Initializing LangGraph Agent")
                logger.info("=" * 70)
                logger.info(f"MCP Enabled: {self.use_mcp}")
                logger.info(f"RAG Enabled: {self.use_rag}")
                logger.info(f"Tools Enabled: {self.enable_mcp_tools}")
                logger.info("=" * 70)
                
                self.agent = ChatbotAgent(
                    provider_name=self.provider_name,
                    model=None,  # Use default from Config
                    temperature=self.temperature,
                    enable_tools=self.enable_mcp_tools,
                    rag_service=self.rag_service if self.use_rag else None,
                    use_mcp=self.use_mcp  # Use the configured MCP setting
                )
                logger.info("Initialized LangGraph Agent")
            except Exception as e:
                logger.warning(f"Failed to initialize LangGraph Agent: {e}")
                logger.info("Falling back to keyword-based routing")
                self.use_agent = False
    
    def _initialize_provider(self):
        """Initialize the LLM provider(s) based on configuration."""
        try:
            # Get API key and model for primary provider
            api_key = Config.get_llm_api_key()
            model = Config.get_llm_model()
            
            if not api_key:
                raise ValueError(
                    f"No API key found for provider '{self.provider_name}'. "
                    f"Please set the appropriate API key in your environment variables."
                )
            
            # Create primary provider
            primary_provider = LLMRouter.get_provider(
                provider_name=self.provider_name,
                api_key=api_key,
                model=model
            )
            
            # Create fallback providers if enabled
            fallback_providers = []
            if self.use_fallback:
                fallback_providers = self._create_fallback_providers()
            
            # Use provider manager if fallbacks are available, otherwise use primary directly
            if fallback_providers:
                self.provider_manager = LLMProviderManager(
                    primary_provider=primary_provider,
                    fallback_providers=fallback_providers
                )
                self.llm_provider = None  # Use manager instead
            else:
                self.llm_provider = primary_provider
                self.provider_manager = None
            
            logger.info(f"Initialized LLM provider: {self.provider_name} ({model})")
            if fallback_providers:
                logger.info(f"Fallback providers enabled: {len(fallback_providers)}")
                
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize LLM provider: {e}\n"
                f"Please check your configuration and API keys."
            )
    
    def _create_fallback_providers(self) -> List:
        """Create fallback providers from available API keys."""
        fallbacks = []
        
        # Try to add other providers as fallbacks
        providers_to_try = ['openai', 'gemini', 'deepseek']
        providers_to_try.remove(self.provider_name.lower())
        
        for provider in providers_to_try:
            try:
                if provider == 'openai' and Config.OPENAI_API_KEY:
                    fallback = LLMRouter.get_provider(
                        provider_name='openai',
                        api_key=Config.OPENAI_API_KEY,
                        model=Config.OPENAI_MODEL
                    )
                    fallbacks.append(fallback)
                elif provider == 'gemini' and Config.GEMINI_API_KEY:
                    fallback = LLMRouter.get_provider(
                        provider_name='gemini',
                        api_key=Config.GEMINI_API_KEY,
                        model=Config.GEMINI_MODEL
                    )
                    fallbacks.append(fallback)
                elif provider == 'deepseek' and Config.DEEPSEEK_API_KEY:
                    fallback = LLMRouter.get_provider(
                        provider_name='deepseek',
                        api_key=Config.DEEPSEEK_API_KEY,
                        model=Config.DEEPSEEK_MODEL
                    )
                    fallbacks.append(fallback)
            except Exception:
                # Skip if provider can't be initialized
                continue
        
        return fallbacks
    
    def switch_provider(self, provider_name: str):
        """
        Switch the LLM provider dynamically.
        
        Args:
            provider_name: Name of the provider to switch to ('openai', 'gemini', 'deepseek')
        """
        provider_name = provider_name.lower()
        
        if provider_name not in ['openai', 'gemini', 'deepseek']:
            raise ValueError(f"Unknown provider '{provider_name}'. Available: openai, gemini, deepseek")
        
        # Get API key and model for the new provider
        if provider_name == 'openai':
            api_key = Config.OPENAI_API_KEY
            model = Config.OPENAI_MODEL
        elif provider_name == 'gemini':
            api_key = Config.GEMINI_API_KEY
            model = Config.GEMINI_MODEL
        elif provider_name == 'deepseek':
            api_key = Config.DEEPSEEK_API_KEY
            model = Config.DEEPSEEK_MODEL
        else:
            raise ValueError(f"Provider '{provider_name}' not configured")
        
        if not api_key:
            raise ValueError(f"API key not found for provider '{provider_name}'. Please configure it in your environment.")
        
        # Create new primary provider
        new_provider = LLMRouter.get_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )
        
        # Update provider
        self.provider_name = provider_name
        self.llm_provider = new_provider
        self.provider_manager = None  # Reset manager, can recreate if needed
        
        # Update agent if it exists
        if self.use_agent and self.agent:
            try:
                # Update agent's provider name and reinitialize LLM
                self.agent.provider_name = provider_name
                # Reinitialize LLM with new provider
                self.agent.llm = self.agent._initialize_llm(model)
                logger.info(f"Updated agent with new provider: {provider_name} ({model})")
            except Exception as e:
                logger.warning(f"Failed to update agent LLM directly: {e}")
                # Try to reinitialize the entire agent as fallback
                try:
                    self.agent = ChatbotAgent(
                        provider_name=self.provider_name,
                        model=model,
                        temperature=self.temperature,
                        enable_tools=self.enable_mcp_tools,
                        rag_service=self.rag_service if self.use_rag else None,
                        use_mcp=self.use_mcp
                    )
                    logger.info(f"Reinitialized agent with new provider: {provider_name} ({model})")
                except Exception as e2:
                    logger.warning(f"Failed to reinitialize agent: {e2}")
        
        logger.info(f"Switched LLM provider to: {provider_name} ({model})")
    
    def _initialize_tools(self):
        """Initialize MCP tools (Jira, Confluence) on demand."""
        if self._tools_initialized or not self.enable_mcp_tools:
            return
        
        try:
            self.jira_tool = JiraTool()
            logger.info("Initialized Jira Tool")
            
            # Initialize Confluence Tool
            try:
                self.confluence_tool = ConfluenceTool()
                logger.info("Initialized Confluence Tool")
            except ValueError as e:
                # Configuration error - provide helpful message
                logger.warning(f"Confluence Tool not available: {e}")
                logger.info("To enable Confluence page creation, set in .env:")
                logger.info("CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki")
                logger.info("CONFLUENCE_SPACE_KEY=YOUR_SPACE_KEY")
            except Exception as e:
                logger.warning(f"Failed to initialize Confluence Tool: {e}")
            
            # Initialize Jira Maturity Evaluator if Jira tool is available
            if self.jira_tool:
                try:
                    # Get LLM provider for evaluator
                    if self.provider_manager:
                        evaluator_llm = self.provider_manager.primary
                    else:
                        evaluator_llm = self.llm_provider
                    
                    self.jira_evaluator = JiraMaturityEvaluator(
                        jira_url=Config.JIRA_URL,
                        jira_email=Config.JIRA_EMAIL,
                        jira_api_token=Config.JIRA_API_TOKEN,
                        project_key=Config.JIRA_PROJECT_KEY,
                        llm_provider=evaluator_llm
                    )
                    logger.info("Initialized Jira Maturity Evaluator")
                except Exception as e:
                    logger.warning(f"Failed to initialize Jira Evaluator: {e}")
            
            self._tools_initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize Jira Tool: {e}")
            # Don't set _tools_initialized = True so we can retry later
    
    def _build_prompt(self, user_input: str) -> str:
        """
        Build the full prompt including conversation history and RAG context.
        
        Args:
            user_input: Current user message
            
        Returns:
            Formatted prompt string
        """
        # Get RAG context if enabled
        rag_context = ""
        if self.use_rag and self.rag_service:
            try:
                rag_context = self.rag_service.get_context(user_input, top_k=self.rag_top_k)
            except Exception as e:
                logger.warning(f"RAG retrieval error: {e}")
                rag_context = ""
        
        # Get conversation context (from persistent memory or in-memory)
        if self.use_persistent_memory and self.memory_manager and self.conversation_id:
            # Get optimized context from memory manager
            context_messages = self.memory_manager.get_conversation_context(
                self.conversation_id,
                max_messages=self.max_history * 2
            )
        else:
            # Use in-memory history
            context_messages = self.conversation_history[-self.max_history * 2:]
        
        # Build context from messages
        context_parts = []
        
        # Add RAG context first if available
        if rag_context:
            context_parts.append(rag_context)
            context_parts.append("")  # Empty line separator
        
        for msg in context_messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if role == 'user':
                context_parts.append(f"User: {content}")
            elif role == 'assistant':
                context_parts.append(f"Assistant: {content}")
            elif role == 'system':
                # System messages (like summaries) are already formatted
                context_parts.append(content)
        
        # Add current user input
        context_parts.append(f"User: {user_input}")
        context_parts.append("Assistant:")
        
        # Combine system prompt with conversation context
        full_prompt = "\n".join(context_parts)
        return full_prompt
    
    def get_response(self, user_input: str) -> str:
        """
        Get a response from the LLM for the given user input.
        
        Args:
            user_input: User's message
            
        Returns:
            AI assistant's response
        """
        if not user_input.strip():
            return "I'm here! What would you like to talk about?"
        
        # Check for exit commands
        user_input_lower = user_input.lower().strip()
        if user_input_lower in ['bye', 'exit', 'quit', 'goodbye']:
            return "Goodbye! It was great chatting with you. Have a wonderful day!"
        
        # Use LangGraph agent if enabled
        if self.use_agent and self.agent:
            try:
                # Get conversation history for agent
                conversation_history = []
                if self.use_persistent_memory and self.memory_manager and self.conversation_id:
                    messages = self.memory_manager.get_conversation_messages(self.conversation_id)
                    conversation_history = [
                        {"role": msg.get('role', 'user'), "content": msg.get('content', '')}
                        for msg in messages
                    ]
                else:
                    # Use in-memory history
                    conversation_history = self.conversation_history
                
                # Invoke agent
                response = self.agent.invoke(user_input, conversation_history)
                
                # Save to memory
                if self.use_persistent_memory and self.memory_manager:
                    if not self.conversation_id:
                        from datetime import datetime
                        self.conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        self.memory_manager.create_conversation(
                            self.conversation_id,
                            title=user_input[:50] + ('...' if len(user_input) > 50 else '')
                        )
                    
                    self.memory_manager.add_message(self.conversation_id, 'user', user_input)
                    self.memory_manager.add_message(self.conversation_id, 'assistant', response)
                
                # Also update in-memory history
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": response})
                
                return response
            except Exception as e:
                logger.error(f"Error in agent: {e}", exc_info=True)
                # Fall back to keyword-based routing
                pass
        
        # Fallback: Check for Jira creation intent (keyword-based)
        # Support multiple keyword variations
        jira_keywords = [
            "create the jira",
            "create jira",
            "create a jira",
            "make a jira",
            "create jira ticket",
            "create jira issue",
            "create jira backlog",
            "create jira story",
            "add jira",
            "new jira"
        ]
        
        if any(keyword in user_input_lower for keyword in jira_keywords):
            # Initialize tools if needed (lazy loading)
            if self.enable_mcp_tools and self.lazy_load_tools:
                self._initialize_tools()
            return self._handle_jira_creation(user_input)
        
        try:
            # Build prompt with conversation history
            user_prompt = self._build_prompt(user_input)
            
            # Generate response using provider manager or direct provider
            if self.provider_manager:
                response = self.provider_manager.generate_response(
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.temperature,
                    json_mode=False
                )
            else:
                response = self.llm_provider.generate_response(
                    system_prompt=self.system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.temperature,
                    json_mode=False
                )
            
            # Save to persistent memory if enabled
            if self.use_persistent_memory and self.memory_manager:
                if not self.conversation_id:
                    # Create new conversation
                    from datetime import datetime
                    self.conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.memory_manager.create_conversation(
                        self.conversation_id,
                        title=user_input[:50] + ('...' if len(user_input) > 50 else '')
                    )
                
                # Add messages to persistent storage
                self.memory_manager.add_message(
                    self.conversation_id,
                    role='user',
                    content=user_input
                )
                self.memory_manager.add_message(
                    self.conversation_id,
                    role='assistant',
                    content=response
                )
                
                # Check if summarization is needed
                messages = self.memory_manager.get_conversation_messages(self.conversation_id)
                if self.memory_summarizer and self.memory_summarizer.should_summarize(len(messages)):
                    conversation = self.memory_manager.get_conversation(self.conversation_id)
                    existing_summary = conversation.get('summary') if conversation else None
                    
                    # Get messages that need summarization (older messages)
                    messages_to_summarize = messages[:-self.max_history * 2] if len(messages) > self.max_history * 2 else []
                    
                    if messages_to_summarize:
                        new_summary = self.memory_summarizer.summarize_conversation(
                            messages_to_summarize,
                            existing_summary=existing_summary
                        )
                        self.memory_manager.update_conversation_summary(
                            self.conversation_id,
                            new_summary
                        )
            
            # Also update in-memory history for backward compatibility
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Trim history if it exceeds max_history
            if len(self.conversation_history) > self.max_history * 2:
                self.conversation_history = self.conversation_history[-self.max_history * 2:]
            
            return response
            
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            logger.error(f"Error in get_response: {e}", exc_info=True)
            return error_msg

    def _handle_jira_creation(self, user_input: str) -> str:
        """Handle the creation of a Jira issue based on conversation context."""
        if not self.jira_tool:
            return "I apologize, but the Jira tool is not configured correctly. Please check your Jira credentials."
            
        # 1. Analyze context and generate backlog details
        logger.info("Analyzing conversation to create Jira backlog...")
        
        # Gather context
        context_str = ""
        recent_history = self.conversation_history[-self.max_history * 2:]
        for msg in recent_history:
            context_str += f"{msg['role']}: {msg['content']}\n"
        context_str += f"user: {user_input}\n"
        
        generation_prompt = f"""
        Based on the conversation context below, create a comprehensive Jira backlog item.
        The user's intent is triggered by "create the jira".
        
        CONTEXT:
        {context_str}
        
        REQUIREMENTS:
        1. Summary: Concise title
        2. Business Value: Why this is important
        3. Acceptance Criteria: List of verifyable criteria
        4. Priority: High, Medium, or Low (infer from context, default to Medium)
        5. INVEST Analysis: Brief check against INVEST principles (Independent, Negotiable, Valuable, Estimable, Small, Testable)
        
        OUTPUT FORMAT:
        Provide a valid JSON object with the following keys:
        {{
            "summary": "...",
            "business_value": "...",
            "acceptance_criteria": ["...", "..."],
            "priority": "...",
            "invest_analysis": "...",
            "description": "..." 
        }}
        
        Note: The 'description' field should be a formatted string combining Business Value, AC, and INVEST analysis suitable for the Jira description field.
        """
        
        try:
            # Generate JSON content
            if self.provider_manager:
                response = self.provider_manager.generate_response(
                    system_prompt="You are a Jira Product Owner assistant.",
                    user_prompt=generation_prompt,
                    json_mode=True
                )
            else:
                response = self.llm_provider.generate_response(
                    system_prompt="You are a Jira Product Owner assistant.",
                    user_prompt=generation_prompt,
                    json_mode=True
                )
            
            # Parse JSON
            # Clean up markdown code blocks if present
            cleaned_response = response.replace("```json", "").replace("```", "").strip()
            backlog_data = json.loads(cleaned_response)
            
            # 2. Create Issue
            result = self.jira_tool.create_issue(
                summary=backlog_data.get('summary'),
                description=backlog_data.get('description'),
                priority=backlog_data.get('priority', 'Medium')
            )
            
            if result.get('success'):
                issue_key = result['key']
                response_text = (
                    f"✅ Successfully created Jira issue: **{issue_key}**\n"
                    f"Summary: {backlog_data.get('summary')}\n"
                    f"Link: {result['link']}\n\n"
                    f"Backlog Details:\n"
                    f"- Priority: {backlog_data.get('priority')}\n"
                    f"- Business Value: {backlog_data.get('business_value')}\n\n"
                )
                
                # 3. Evaluate the newly created issue
                if self.jira_evaluator:
                    try:
                        logger.info(f"Evaluating maturity for {issue_key}...")
                        
                        # Fetch the created issue from Jira
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
                            # Format evaluation results
                            response_text += (
                                f"📊 **Maturity Evaluation Results:**\n"
                                f"Overall Maturity Score: **{evaluation['overall_maturity_score']}/100**\n\n"
                            )
                            
                            # Add strengths if available
                            if evaluation.get('strengths'):
                                response_text += "**Strengths:**\n"
                                for strength in evaluation['strengths']:
                                    response_text += f"  ✓ {strength}\n"
                                response_text += "\n"
                            
                            # Add weaknesses if available
                            if evaluation.get('weaknesses'):
                                response_text += "**Areas for Improvement:**\n"
                                for weakness in evaluation['weaknesses']:
                                    response_text += f"  - {weakness}\n"
                                response_text += "\n"
                            
                            # Add recommendations if available
                            if evaluation.get('recommendations'):
                                response_text += "**Recommendations:**\n"
                                for rec in evaluation['recommendations']:
                                    response_text += f"  → {rec}\n"
                                response_text += "\n"
                            
                            # Add detailed scores if available
                            if evaluation.get('detailed_scores'):
                                response_text += "**Detailed Scores:**\n"
                                for criterion, score in evaluation['detailed_scores'].items():
                                    criterion_name = criterion.replace('_', ' ').title()
                                    response_text += f"  - {criterion_name}: {score}/100\n"
                            
                            # 4. Create Confluence page after evaluation
                            if self.confluence_tool:
                                try:
                                    logger.info(f"Creating Confluence page for {issue_key}...")
                                    
                                    # Format Confluence page content
                                    confluence_content = self._format_confluence_page(
                                        issue_key=issue_key,
                                        summary=backlog_data.get('summary'),
                                        business_value=backlog_data.get('business_value'),
                                        acceptance_criteria=backlog_data.get('acceptance_criteria', []),
                                        priority=backlog_data.get('priority'),
                                        invest_analysis=backlog_data.get('invest_analysis'),
                                        evaluation=evaluation,
                                        jira_link=result['link']
                                    )
                                    
                                    # Create Confluence page
                                    confluence_result = self.confluence_tool.create_page(
                                        title=f"{issue_key}: {backlog_data.get('summary')}",
                                        content=confluence_content
                                    )
                                    
                                    if confluence_result.get('success'):
                                        response_text += (
                                            f"\n📄 **Confluence Page Created:**\n"
                                            f"Title: {confluence_result['title']}\n"
                                            f"Link: {confluence_result['link']}\n"
                                        )
                                    else:
                                        error_msg = confluence_result.get('error', 'Unknown error')
                                        response_text += (
                                            f"\n⚠ **Confluence page creation failed:**\n"
                                            f"Error: {error_msg}\n\n"
                                            f"**To enable Confluence page creation, please configure:**\n"
                                            f"- CONFLUENCE_URL in your .env file\n"
                                            f"- CONFLUENCE_SPACE_KEY in your .env file\n"
                                            f"See CONFLUENCE_SETUP.md for details.\n"
                                        )
                                        
                                except Exception as e:
                                    response_text += f"\n⚠ Confluence page creation failed: {str(e)}\n"
                                    logger.error(f"Error creating Confluence page: {e}", exc_info=True)
                        else:
                            response_text += f"⚠ Could not evaluate maturity: {evaluation.get('error', 'Unknown error')}\n"
                            
                    except Exception as e:
                        response_text += f"⚠ Maturity evaluation failed: {str(e)}\n"
                        logger.error(f"Error during evaluation: {e}", exc_info=True)
                
                return response_text
            else:
                return f"❌ Failed to create Jira issue: {result.get('error')}"
                
        except Exception as e:
            return f"❌ Error processing Jira creation request: {str(e)}"
    
    def _format_confluence_page(self, issue_key: str, summary: str, business_value: str,
                               acceptance_criteria: List[str], priority: str, invest_analysis: str,
                               evaluation: Dict, jira_link: str) -> str:
        """
        Format content for Confluence page.
        
        Returns HTML content for the Confluence page.
        """
        html_content = f"""
<h1>{issue_key}: {summary}</h1>

<h2>Overview</h2>
<p><strong>Jira Issue:</strong> <a href="{jira_link}">{issue_key}</a></p>
<p><strong>Priority:</strong> {priority}</p>

<h2>Business Value</h2>
<p>{business_value}</p>

<h2>Acceptance Criteria</h2>
<ul>
"""
        for ac in acceptance_criteria:
            html_content += f"<li>{ac}</li>\n"
        
        html_content += "</ul>\n"
        
        html_content += f"""
<h2>INVEST Analysis</h2>
<p>{invest_analysis}</p>
"""
        
        if 'error' not in evaluation:
            html_content += f"""
<h2>Maturity Evaluation</h2>
<p><strong>Overall Maturity Score: {evaluation['overall_maturity_score']}/100</strong></p>

<h3>Strengths</h3>
<ul>
"""
            for strength in evaluation.get('strengths', []):
                html_content += f"<li>{strength}</li>\n"
            
            html_content += "</ul>\n"
            
            html_content += """
<h3>Areas for Improvement</h3>
<ul>
"""
            for weakness in evaluation.get('weaknesses', []):
                html_content += f"<li>{weakness}</li>\n"
            
            html_content += "</ul>\n"
            
            html_content += """
<h3>Recommendations</h3>
<ul>
"""
            for rec in evaluation.get('recommendations', []):
                html_content += f"<li>{rec}</li>\n"
            
            html_content += "</ul>\n"
            
            if evaluation.get('detailed_scores'):
                html_content += """
<h3>Detailed Scores</h3>
<table>
<thead>
<tr>
<th>Criterion</th>
<th>Score</th>
</tr>
</thead>
<tbody>
"""
                for criterion, score in evaluation['detailed_scores'].items():
                    criterion_name = criterion.replace('_', ' ').title()
                    html_content += f"<tr><td>{criterion_name}</td><td>{score}/100</td></tr>\n"
                
                html_content += """
</tbody>
</table>
"""
        
        return html_content

    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        if self.use_persistent_memory and self.memory_manager and self.conversation_id:
            # Note: We don't delete the conversation, just clear local history
            # To delete conversation, use delete_conversation()
            pass
        logger.info("Conversation history cleared.")
    
    def get_history_summary(self) -> str:
        """Get a summary of the conversation history."""
        if self.use_persistent_memory and self.memory_manager and self.conversation_id:
            conversation = self.memory_manager.get_conversation(self.conversation_id)
            if conversation:
                message_count = len(conversation.get('messages', []))
                turns = message_count // 2
                summary = conversation.get('summary', '')
                if summary:
                    return f"Conversation has {turns} turn(s). Summary: {summary[:100]}..."
                return f"Conversation has {turns} turn(s) in history."
        
        if not self.conversation_history:
            return "No conversation history yet."
        
        turns = len(self.conversation_history) // 2
        return f"Conversation has {turns} turn(s) in history."
    
    def load_conversation(self, conversation_id: str) -> bool:
        """
        Load a conversation from persistent memory.
        
        Args:
            conversation_id: Conversation ID to load
            
        Returns:
            True if successful, False otherwise
        """
        if not self.use_persistent_memory or not self.memory_manager:
            return False
        
        conversation = self.memory_manager.get_conversation(conversation_id)
        if not conversation:
            return False
        
        self.conversation_id = conversation_id
        
        # Load messages into conversation history
        self.conversation_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in conversation.get('messages', [])
        ]
        
        return True
    
    def set_conversation_id(self, conversation_id: str):
        """Set the current conversation ID."""
        self.conversation_id = conversation_id
        if self.use_persistent_memory and self.memory_manager:
            # Ensure conversation exists
            conversation = self.memory_manager.get_conversation(conversation_id)
            if not conversation:
                self.memory_manager.create_conversation(conversation_id, title="New Chat")
    
    def run(self):
        """
        Run the chatbot in interactive mode.
        """
        print("=" * 70)
        print("🤖 LLM-Powered Chatbot")
        print("=" * 70)
        print(f"Provider: {self.provider_name}")
        print(f"Model: {Config.get_llm_model()}")
        print(f"Temperature: {self.temperature}")
        print(f"Max History: {self.max_history} turns")
        print("\nCommands:")
        print("  - Type your message and press Enter")
        print("  - Type 'bye', 'exit', or 'quit' to end the conversation")
        print("  - Type '/clear' to clear conversation history")
        print("  - Type '/history' to see conversation summary")
        print("=" * 70)
        print()
        
        # Simple greeting without API call to avoid blocking
        print("Chatbot: Hello! I'm ready to chat. How can I help you today?\n")
        sys.stdout.flush()
        
        # Main conversation loop
        while True:
            try:
                # Ensure prompt is displayed
                sys.stdout.flush()
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() == '/clear':
                    self.clear_history()
                    continue
                elif user_input.lower() == '/history':
                    print(f"Chatbot: {self.get_history_summary()}\n")
                    continue
                
                # Get and display response
                response = self.get_response(user_input)
                print(f"Chatbot: {response}\n")
                
                # Check if user wants to exit
                if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye']:
                    break
                    
            except KeyboardInterrupt:
                print("\n\nChatbot: Goodbye! Thanks for chatting!")
                break
            except EOFError:
                print("\n\nChatbot: Goodbye! Thanks for chatting!")
                break
            except Exception as e:
                logger.error(f"Unexpected error in run loop: {e}", exc_info=True)
                print(f"\n[Unexpected error: {e}]\n")


def main():
    """Main entry point for the chatbot."""
    try:
        logger.info("Initializing chatbot...")
        print("Initializing chatbot...")
        sys.stdout.flush()
        
        # Validate configuration
        if not Config.validate():
            logger.warning("Configuration validation failed")
            print("⚠ Warning: Configuration validation failed.")
            print("Some features may not work correctly.")
            print("Please check your environment variables or .env file.\n")
            sys.stdout.flush()
        
        logger.info("Creating chatbot instance...")
        print("Creating chatbot instance...")
        sys.stdout.flush()
        
        # Create and run chatbot
        chatbot = Chatbot(
            provider_name=None,  # Use default from Config
            use_fallback=True,
            temperature=0.7,
            max_history=10
        )
        
        logger.info("Starting chatbot...")
        print("Starting chatbot...")
        sys.stdout.flush()
        
        chatbot.run()
        
    except Exception as e:
        logger.error(f"Failed to start chatbot: {e}", exc_info=True)
        print(f"\n❌ Failed to start chatbot: {e}")
        print("\nPlease ensure:")
        print("  1. Required dependencies are installed: pip install -r requirements.txt")
        print("  2. LLM_PROVIDER environment variable is set (e.g., 'openai', 'gemini', 'deepseek')")
        print("  3. Appropriate API key is set (e.g., OPENAI_API_KEY, GEMINI_API_KEY, DEEPSEEK_API_KEY)")
        print("  4. Model name is set (e.g., OPENAI_MODEL, GEMINI_MODEL, DEEPSEEK_MODEL)")
        sys.exit(1)


if __name__ == "__main__":
    main()