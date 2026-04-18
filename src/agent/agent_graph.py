"""
LangGraph Agent for Chatbot with Tool Orchestration.

This agent uses LangGraph to intelligently route user requests and orchestrate
tools (Jira, Confluence, RAG) based on user intent.
"""

import copy
from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = False
    ChatGoogleGenerativeAI = None
except Exception as e:
    # Handle other import errors (e.g., version conflicts)
    LANGCHAIN_GOOGLE_GENAI_AVAILABLE = False
    ChatGoogleGenerativeAI = None
import json
import concurrent.futures

from src.tools.jira_tool import JiraTool
from src.tools.confluence_tool import ConfluenceTool
from src.runtime import build_application_services
from src.services.atlassian_mcp_support_service import AtlassianMcpSupportService
from src.services.chat_response_service import ChatResponseService
from src.services.confluence_creation_service import ConfluenceCreationService
from src.services.coze_agent_service import CozeAgentService
from src.services.general_chat_service import GeneralChatService
from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.services.rag_ingestion_service import RagIngestionService
from src.services.rag_query_service import RagQueryService
from src.services.coze_client import CozeClient
from src.services.intent_detector import IntentDetector
from src.services.requirement_sdlc_agent_service import (
    RequirementSdlcAgentService,
)
from src.mcp.mcp_integration import MCPIntegration
from src.agent.graph_builder import build_agent_graph
from src.agent.callbacks import LLMMonitoringCallback
from src.agent.confluence_nodes import (
    build_confluence_exception_outcome,
    build_confluence_failure_outcome,
    build_confluence_success_outcome,
)
from src.agent.intent_routing import detect_keyword_intent
from src.agent.jira_nodes import (
    build_jira_exception_outcome,
    build_jira_failure_outcome,
    build_jira_success_outcome,
)
from src.services.agent_intent_service import AgentIntentService
from config.config import Config
from src.utils.logger import get_logger

# Initialize logger for this module
logger = get_logger('chatbot.agent')

# Log langchain-google-genai availability
if not LANGCHAIN_GOOGLE_GENAI_AVAILABLE:
    logger.warning("langchain_google_genai not available. Gemini will use direct google-generativeai integration.")
logger = get_logger('chatbot.agent')


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[List[BaseMessage], "Conversation messages"]
    user_input: str
    intent: Optional[str]  # 'jira_creation', 'general_chat', 'rag_query', 'coze_agent', etc.
    jira_result: Optional[Dict[str, Any]]
    evaluation_result: Optional[Dict[str, Any]]
    confluence_result: Optional[Dict[str, Any]]
    rag_context: Optional[List[str]]
    coze_result: Optional[Dict[str, Any]]
    conversation_history: List[Dict[str, str]]
    next_action: Optional[str]  # Next node to execute


class ChatbotAgent:
    """
    LangGraph-based agent for intelligent chatbot with tool orchestration.
    """
    
    def _get_cloud_id(self) -> Optional[str]:
        """Delegate cloudId resolution to the Atlassian support helper."""
        self._refresh_helper_services()
        return self.atlassian_support_service.get_cloud_id()
    
    def _get_space_id(self, space_key: str, cloud_id: Optional[str] = None) -> Optional[int]:
        """Delegate Confluence space-id resolution to the Atlassian support helper."""
        self._refresh_helper_services()
        return self.atlassian_support_service.get_space_id(space_key, cloud_id)
    
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
            provider_name: LLM provider ('openai', 'gemini', or 'deepseek')
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
        
        # Initialize LLM monitoring callback (before LLM initialization)
        # Wrapped in try/except to ensure callback issues don't break LLM init
        self.llm_callback = None
        try:
            self.llm_callback = LLMMonitoringCallback()
            logger.debug("LLM monitoring callback initialized")
        except Exception as e:
            logger.warning(f"Could not initialize LLM monitoring callback: {e}. Continuing without monitoring.")
        
        # Initialize LLM
        self.llm = self._initialize_llm(model)
        
        # Initialize MCP integration if enabled
        self.mcp_integration = None
        if self.use_mcp:
            try:
                self.mcp_integration = MCPIntegration(use_mcp=True)
                # Initialize MCP asynchronously (will be done on first use)
                logger.info("MCP integration enabled - will initialize on first use")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP integration: {e}")
                logger.info("Falling back to custom tools")
                self.use_mcp = False
                self.mcp_integration = None
        
        # Initialize tools (always initialize custom tools as fallback)
        self.jira_tool = None
        self.confluence_tool = None
        self.jira_evaluator = None
        self.jira_issue_port = None
        self.confluence_page_port = None
        self.jira_evaluation_port = None
        self.requirement_workflow_service = None
        self.requirement_sdlc_agent_service = None
        self.chat_response_service = None
        self.general_chat_service = None
        self.confluence_creation_service = None
        self.rag_query_service = None
        self.coze_agent_service = None
        self.atlassian_support_service = None
        self.rag_ingestion_service = None
        self.intent_service = None
        self._requirement_sdlc_agent_state: Optional[Dict[str, Any]] = None
        self._selected_agent_mode: str = "auto"
        self._latest_requirement_workflow_progress: Optional[List[Dict[str, Any]]] = None
        
        if self.enable_tools:
            self._initialize_tools()
            self._compose_application_services()
        
        # Initialize Coze client if enabled
        self.coze_client = None
        if Config.COZE_ENABLED:
            try:
                self.coze_client = CozeClient()
                if self.coze_client.is_configured():
                    logger.info("Coze client initialized successfully")
                else:
                    logger.warning("Coze is enabled but not properly configured (missing API token or bot ID)")
                    self.coze_client = None
            except Exception as e:
                logger.warning(f"Failed to initialize Coze client: {e}")
                self.coze_client = None

        self._compose_flow_services()
        self._compose_intent_service()
        self._compose_helper_services()
        
        # Initialize intent detector (lazy initialization - will be created on first use)
        self.intent_detector: Optional[IntentDetector] = None
        
        # Initialize intent cache for avoiding redundant LLM calls
        self._intent_cache: Dict[str, Dict[str, Any]] = {}
        self._intent_cache_max_size = 100  # Cache last 100 detections
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _initialize_llm(self, model: Optional[str] = None):
        """Initialize the LLM based on provider."""
        # Get callback list (only if callback was successfully initialized)
        callback_list = [self.llm_callback] if self.llm_callback else None
        
        if self.provider_name == "openai":
            api_key = Config.OPENAI_API_KEY
            model_name = model or Config.OPENAI_MODEL
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in configuration")
            
            # Validate API key format (should start with 'sk-')
            if not api_key.startswith('sk-'):
                logger.warning("OpenAI API key format may be invalid (should start with 'sk-')")
            
            # Validate model name (fix common issues)
            if model_name == "gpt-4.1":
                logger.warning("Model 'gpt-4.1' may be invalid. Using 'gpt-4' instead.")
                model_name = "gpt-4"
            elif "gpt-4" not in model_name.lower() and "gpt-3.5" not in model_name.lower():
                logger.warning(f"Model '{model_name}' may not be valid. Common models: gpt-4, gpt-4-turbo, gpt-3.5-turbo")
            
            try:
                # Try with timeout and max_retries (LangChain 0.1.0+)
                llm = ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                    timeout=60.0,  # Increased timeout to 60 seconds for better reliability
                    max_retries=2,  # Increased retries for better reliability
                    callbacks=callback_list  # Add monitoring callback (optional)
                )
                logger.info(f"LLM initialized: {self.provider_name} ({model_name})")
                return llm
            except TypeError:
                # Fallback if parameters not supported
                logger.warning("LLM timeout parameter not supported, using default")
                return ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                    callbacks=callback_list  # Add monitoring callback (optional)
                )
            except Exception as e:
                logger.error(f"LLM initialization error: {e}")
                raise
        elif self.provider_name == "gemini":
            api_key = Config.GEMINI_API_KEY
            model_name = model or Config.GEMINI_MODEL
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in configuration")
            
            if not LANGCHAIN_GOOGLE_GENAI_AVAILABLE:
                raise ImportError(
                    "langchain_google_genai is not available. "
                    "Install with: pip install langchain-google-genai. "
                    "Note: There may be version conflicts with google-ai-generativelanguage. "
                    "The chatbot will still work with Gemini using direct google-generativeai integration."
                )
            
            try:
                # Try with timeout and max_retries
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=self.temperature,
                    google_api_key=api_key,
                    timeout=30.0,  # Add timeout to LLM calls
                    max_retries=2,  # Limit retries to avoid long waits
                    callbacks=callback_list  # Add monitoring callback (optional)
                )
            except TypeError:
                # Fallback if parameters not supported
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=self.temperature,
                    google_api_key=api_key,
                    callbacks=callback_list  # Add monitoring callback (optional)
                )
        elif self.provider_name == "deepseek":
            api_key = Config.DEEPSEEK_API_KEY
            model_name = model or Config.DEEPSEEK_MODEL
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in configuration")
            
            # DeepSeek uses OpenAI-compatible API, so we use ChatOpenAI with custom base_url
            try:
                # Try with timeout and max_retries (LangChain 0.1.0+)
                llm = ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url="https://api.deepseek.com",
                    timeout=60.0,  # Increased timeout to 60 seconds for DeepSeek API
                    max_retries=2,  # Increased retries for better reliability
                    callbacks=callback_list  # Add monitoring callback (optional)
                )
                logger.info(f"LLM initialized: {self.provider_name} ({model_name})")
                return llm
            except TypeError:
                # Fallback if parameters not supported
                logger.warning("LLM timeout parameter not supported, using default")
                return ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url="https://api.deepseek.com",
                    callbacks=callback_list  # Add monitoring callback (optional)
                )
            except Exception as e:
                logger.error(f"LLM initialization error: {e}")
                raise
        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
    
    def _initialize_tools(self):
        """Initialize Jira and Confluence tools."""
        try:
            self.jira_tool = JiraTool()
        except Exception as e:
            logger.warning(f"Failed to initialize Jira Tool: {e}")
        
        try:
            self.confluence_tool = ConfluenceTool()
        except Exception as e:
            logger.warning(f"Failed to initialize Confluence Tool: {e}")
        
        # Initialize Jira evaluator if Jira tool is available
        if self.jira_tool:
            try:
                from src.llm import LLMRouter
                # Get API key and model based on provider
                if self.provider_name == "openai":
                    api_key = Config.OPENAI_API_KEY
                    model = Config.OPENAI_MODEL
                elif self.provider_name == "gemini":
                    api_key = Config.GEMINI_API_KEY
                    model = Config.GEMINI_MODEL
                elif self.provider_name == "deepseek":
                    api_key = Config.DEEPSEEK_API_KEY
                    model = Config.DEEPSEEK_MODEL
                else:
                    # Fallback to OpenAI if provider not recognized
                    api_key = Config.OPENAI_API_KEY
                    model = Config.OPENAI_MODEL
                
                llm_provider = LLMRouter.get_provider(
                    provider_name=self.provider_name,
                    api_key=api_key,
                    model=model
                )
                self.jira_evaluator = JiraMaturityEvaluator(
                    jira_url=Config.JIRA_URL,
                    jira_email=Config.JIRA_EMAIL,
                    jira_api_token=Config.JIRA_API_TOKEN,
                    project_key=Config.JIRA_PROJECT_KEY,
                    llm_provider=llm_provider
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Jira Evaluator: {e}")

    def _compose_application_services(self) -> None:
        """Assemble transport-hiding ports through the shared composition layer."""
        services = build_application_services(
            config=Config,
            llm_provider=self.llm,
            jira_tool=self.jira_tool,
            confluence_tool=self.confluence_tool,
            jira_evaluator=self.jira_evaluator,
            rag_service=getattr(self, "_rag_service", None),
            mcp_integration=self.mcp_integration,
            use_mcp=self.use_mcp,
            get_cloud_id=self._get_cloud_id,
            resolve_space_id=self._get_space_id,
            html_to_markdown=self._html_to_markdown,
        )
        self.requirement_workflow_service = services.workflow_service
        self.jira_issue_port = services.jira_issue_port
        self.confluence_page_port = services.confluence_page_port
        self.jira_evaluation_port = services.jira_evaluation_port

    def _compose_flow_services(self) -> None:
        """Assemble flow services used by the graph handlers."""
        llm = getattr(self, "llm", None)
        provider_name = getattr(self, "provider_name", None)
        rag_service = getattr(self, "_rag_service", None)
        coze_client = getattr(self, "coze_client", None)

        if llm:
            self.chat_response_service = ChatResponseService(
                llm_provider=llm,
                provider_name=provider_name,
            )
            self.general_chat_service = GeneralChatService(
                chat_response_service=self.chat_response_service,
                retrieve_confluence_page_info=self._retrieve_confluence_page_info,
            )
            self.rag_query_service = RagQueryService(
                rag_service=rag_service,
                chat_response_service=self.chat_response_service,
            )
            self.requirement_sdlc_agent_service = RequirementSdlcAgentService(
                llm_provider=llm,
                workflow_service=getattr(self, "requirement_workflow_service", None),
            )
            self.confluence_creation_service = ConfluenceCreationService(
                llm_provider=llm,
                confluence_page_port=getattr(self, "confluence_page_port", None),
            )
        else:
            self.chat_response_service = getattr(self, "chat_response_service", None)
            self.general_chat_service = getattr(self, "general_chat_service", None)
            self.rag_query_service = getattr(self, "rag_query_service", None)
            self.requirement_sdlc_agent_service = getattr(
                self,
                "requirement_sdlc_agent_service",
                None,
            )
            self.confluence_creation_service = getattr(
                self,
                "confluence_creation_service",
                None,
            )

        coze_timeout = (
            float(Config.COZE_API_TIMEOUT)
            if hasattr(Config, "COZE_API_TIMEOUT")
            else 300.0
        )
        if coze_client is not None or getattr(self, "coze_agent_service", None) is None:
            self.coze_agent_service = CozeAgentService(
                coze_client=coze_client,
                timeout_seconds=coze_timeout,
            )

    def _refresh_flow_services(self) -> None:
        """Rebuild flow services from current runtime dependencies before execution."""
        self._compose_flow_services()

    def _compose_intent_service(self) -> None:
        """Assemble the intent-routing service from current runtime dependencies."""
        jira_available = bool(
            getattr(self, "jira_tool", None)
            or (getattr(self, "use_mcp", False) and getattr(self, "mcp_integration", None))
        )
        self.intent_service = AgentIntentService(
            config=Config,
            detect_keyword_intent_fn=detect_keyword_intent,
            rag_service_available=getattr(self, "_rag_service", None) is not None,
            jira_available=jira_available,
            coze_client=getattr(self, "coze_client", None),
            use_mcp=getattr(self, "use_mcp", False),
            mcp_integration=getattr(self, "mcp_integration", None),
            jira_tool=getattr(self, "jira_tool", None),
            get_cached_intent=self._get_cached_intent,
            cache_intent=self._cache_intent,
            initialize_intent_detector=self._initialize_intent_detector,
            confluence_page_port=getattr(self, "confluence_page_port", None),
            has_pending_requirement_sdlc_agent_state=self.has_pending_requirement_sdlc_agent_state,
            get_selected_agent_mode=self.get_selected_agent_mode,
        )

    def _refresh_intent_service(self) -> None:
        """Rebuild the intent-routing service from current mutable dependencies."""
        self._compose_intent_service()

    def _compose_helper_services(self) -> None:
        """Assemble helper services for Atlassian MCP support and RAG ingestion."""
        self.atlassian_support_service = AtlassianMcpSupportService(
            config=Config,
            mcp_integration=getattr(self, "mcp_integration", None),
            use_mcp=getattr(self, "use_mcp", False),
        )
        self.rag_ingestion_service = RagIngestionService(
            rag_service=getattr(self, "_rag_service", None),
        )

    def _refresh_helper_services(self) -> None:
        """Rebuild helper services from current mutable runtime dependencies."""
        self._compose_helper_services()

    def _refresh_application_services(self) -> None:
        """Rebuild ports from current tool/integration references before execution."""
        self._compose_application_services()
        self._compose_flow_services()
        self._compose_intent_service()
        self._compose_helper_services()
    
    def _initialize_intent_detector(self) -> Optional[IntentDetector]:
        """
        Lazily initialize the intent detector if LLM-based detection is enabled.
        
        Returns:
            IntentDetector instance or None if initialization fails or is disabled
        """
        # Check if LLM-based detection is enabled
        if not Config.INTENT_USE_LLM:
            logger.debug("LLM-based intent detection is disabled")
            return None
        
        # Return existing instance if already initialized
        if self.intent_detector is not None:
            return self.intent_detector
        
        try:
            from src.llm import LLMRouter
            
            # Get API key and model based on provider
            if self.provider_name == "openai":
                api_key = Config.OPENAI_API_KEY
                model = Config.OPENAI_MODEL
            elif self.provider_name == "gemini":
                api_key = Config.GEMINI_API_KEY
                model = Config.GEMINI_MODEL
            elif self.provider_name == "deepseek":
                api_key = Config.DEEPSEEK_API_KEY
                model = Config.DEEPSEEK_MODEL
            else:
                # Fallback to OpenAI if provider not recognized
                api_key = Config.OPENAI_API_KEY
                model = Config.OPENAI_MODEL
            
            if not api_key:
                logger.warning("No API key available for intent detector - falling back to keyword-only detection")
                return None
            
            # Create LLM provider for intent detection
            llm_provider = LLMRouter.get_provider(
                provider_name=self.provider_name,
                api_key=api_key,
                model=model
            )
            
            # Create intent detector with configured temperature
            self.intent_detector = IntentDetector(
                llm_provider=llm_provider,
                temperature=Config.INTENT_LLM_TEMPERATURE
            )
            
            logger.info("Intent detector initialized successfully")
            return self.intent_detector
            
        except Exception as e:
            logger.warning(f"Failed to initialize intent detector: {e}")
            logger.info("Falling back to keyword-only intent detection")
            return None
    
    def _get_cached_intent(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Check cache for intent detection result.
        
        Args:
            user_input: User's input message
            
        Returns:
            Cached intent result or None if not found
        """
        import hashlib
        
        # Ensure cache exists (safety check)
        if not hasattr(self, '_intent_cache'):
            self._intent_cache = {}
        
        # Normalize input for cache key (lowercase, strip whitespace)
        normalized_input = user_input.lower().strip()
        cache_key = hashlib.md5(normalized_input.encode()).hexdigest()
        
        if cache_key in self._intent_cache:
            cached_result = self._intent_cache[cache_key]
            logger.debug(f"Intent cache hit for input: '{user_input[:50]}...'")
            return cached_result
        
        return None
    
    def _cache_intent(self, user_input: str, intent_result: Dict[str, Any]):
        """
        Cache intent detection result.
        
        Args:
            user_input: User's input message
            intent_result: Intent detection result to cache
        """
        import hashlib
        
        # Ensure cache exists (safety check)
        if not hasattr(self, '_intent_cache'):
            self._intent_cache = {}
        if not hasattr(self, '_intent_cache_max_size'):
            self._intent_cache_max_size = 100
        
        # Normalize input for cache key
        normalized_input = user_input.lower().strip()
        cache_key = hashlib.md5(normalized_input.encode()).hexdigest()
        
        # Add to cache
        self._intent_cache[cache_key] = intent_result
        
        # Limit cache size (remove oldest entries if over limit)
        if len(self._intent_cache) > self._intent_cache_max_size:
            # Remove oldest entry (simple FIFO - remove first key)
            oldest_key = next(iter(self._intent_cache))
            del self._intent_cache[oldest_key]
            logger.debug(f"Intent cache size limit reached, removed oldest entry")
    
    def _build_graph(self):
        """Build the LangGraph state graph."""
        return build_agent_graph(
            state_type=AgentState,
            detect_intent=self._detect_intent,
            route_after_intent=self._route_after_intent,
            handle_general_chat=self._handle_general_chat,
            handle_jira_creation=self._handle_jira_creation,
            handle_evaluation=self._handle_evaluation,
            route_after_evaluation=self._route_after_evaluation,
            handle_confluence_creation=self._handle_confluence_creation,
            handle_rag_query=self._handle_rag_query,
            handle_coze_agent=self._handle_coze_agent,
            handle_requirement_sdlc_agent=self._handle_requirement_sdlc_agent,
        )

    def load_requirement_sdlc_agent_state(
        self,
        state: Optional[Dict[str, Any]],
    ) -> None:
        """Restore persisted Requirement SDLC Agent state into the agent runtime."""
        self._requirement_sdlc_agent_state = copy.deepcopy(state) if state else None

    def export_requirement_sdlc_agent_state(self) -> Optional[Dict[str, Any]]:
        """Return a copy of the current Requirement SDLC Agent runtime state."""
        return copy.deepcopy(getattr(self, "_requirement_sdlc_agent_state", None))

    def has_pending_requirement_sdlc_agent_state(self) -> bool:
        """Report whether the Requirement SDLC Agent has an active staged turn."""
        state = self.export_requirement_sdlc_agent_state()
        return bool(
            state
            and state.get("stage") in {"analysis", "confirmation"}
        )

    def load_latest_requirement_workflow_progress(
        self,
        workflow_progress: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Restore the latest workflow progress snapshot for request-scoped execution."""
        self._latest_requirement_workflow_progress = (
            copy.deepcopy(workflow_progress) if workflow_progress else None
        )

    def export_latest_requirement_workflow_progress(
        self,
    ) -> Optional[List[Dict[str, Any]]]:
        """Return a copy of the latest workflow progress for UI rendering."""
        return copy.deepcopy(getattr(self, "_latest_requirement_workflow_progress", None))

    def set_selected_agent_mode(self, agent_mode: Optional[str]) -> None:
        """Persist the currently selected agent mode for intent routing."""
        normalized_mode = (agent_mode or "auto").strip().lower()
        self._selected_agent_mode = (
            normalized_mode if normalized_mode in {"auto", "requirement_sdlc_agent"} else "auto"
        )

    def get_selected_agent_mode(self) -> str:
        """Return the currently selected agent mode."""
        return getattr(self, "_selected_agent_mode", "auto")
    
    def _ingest_to_rag(self, content: str, metadata: dict) -> Optional[str]:
        """Delegate RAG ingestion side effects to the helper service."""
        self._refresh_helper_services()
        return self.rag_ingestion_service.ingest(content, metadata)
    
    def _detect_intent(self, state: AgentState) -> AgentState:
        """Detect user intent through the dedicated intent service."""
        self._refresh_intent_service()
        return self.intent_service.detect_intent(state)
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Route to the next node through the dedicated intent service."""
        self._refresh_intent_service()
        return self.intent_service.route_after_intent(state)
    
    def _retrieve_confluence_page_info(self, page_id: str = None, page_title: str = None) -> Dict[str, Any]:
        """Delegate Confluence page retrieval to the Atlassian support helper."""
        self._refresh_helper_services()
        return self.atlassian_support_service.retrieve_confluence_page_info(
            page_id=page_id,
            page_title=page_title,
        )
    
    def _handle_general_chat(self, state: AgentState) -> AgentState:
        """Handle general conversation."""
        self._refresh_flow_services()

        if not self.general_chat_service:
            state["messages"].append(
                AIMessage(
                    content=(
                        "I apologize, but the AI service is not configured correctly."
                    )
                )
            )
            return state

        result = self.general_chat_service.handle(
            user_input=state.get("user_input", ""),
            messages=state.get("messages", []),
            confluence_result=state.get("confluence_result"),
        )
        state["messages"] = result["messages"]
        return state

    def _handle_requirement_sdlc_agent(self, state: AgentState) -> AgentState:
        """Delegate Requirement SDLC Agent turns to the staged agent service."""
        self._refresh_application_services()
        skill_service = getattr(self, "requirement_sdlc_agent_service", None)
        if not skill_service:
            state["messages"].append(
                AIMessage(
                    content=(
                        "I apologize, but the Requirement SDLC Agent is not "
                        "configured correctly."
                    )
                )
            )
            return state

        result = skill_service.handle_turn(
            user_input=state.get("user_input", ""),
            conversation_history=state.get("conversation_history", []),
            pending_state=self.export_requirement_sdlc_agent_state(),
        )
        self.load_requirement_sdlc_agent_state(result.pending_state)
        workflow_progress = None
        if result.workflow_result is not None:
            workflow_progress = getattr(result.workflow_result, "workflow_progress", None)
        self.load_latest_requirement_workflow_progress(workflow_progress)
        state["messages"].append(AIMessage(content=result.response_text))
        return state
    
    def _handle_jira_creation(self, state: AgentState) -> AgentState:
        """Handle Jira issue creation."""
        import datetime
        
        self._refresh_application_services()

        logger.info("Jira Creation: Checking available tools...")
        logger.debug(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.requirement_workflow_service or not self.jira_issue_port:
            error_msg = "Jira tool is not configured. Please check your Jira credentials."
            state["messages"].append(AIMessage(content=error_msg))
            return state
        
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        conversation_history = state.get("conversation_history", [])
        
        try:
            backlog_data = self.requirement_workflow_service.generate_backlog_data_for_agent(
                user_input=user_input,
                messages=messages,
                conversation_history=conversation_history,
            )

            result = self.requirement_workflow_service.create_jira_issue(backlog_data)
            tool_used = result.get("tool_used", "Unknown Tool")

            if result.get("success"):
                created_at = datetime.datetime.now().isoformat()
                success_outcome = build_jira_success_outcome(
                    jira_result=result,
                    backlog_data=backlog_data,
                    tool_used=tool_used,
                    created_at=created_at,
                )
                state["jira_result"] = success_outcome["state"]
                state["messages"].append(AIMessage(
                    content=success_outcome["message"]
                ))
                
                # Ingest Jira issue into RAG knowledge base for future queries
                self._ingest_to_rag(success_outcome["content"], success_outcome["metadata"])
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                failure_outcome = build_jira_failure_outcome(error_msg)
                state["jira_result"] = failure_outcome["state"]
                state["messages"].append(AIMessage(
                    content=failure_outcome["message"]
                ))
        except Exception as e:
            error_msg = f"Error creating Jira issue: {str(e)}"
            exception_outcome = build_jira_exception_outcome(error_msg)
            state["jira_result"] = exception_outcome["state"]
            state["messages"].append(AIMessage(
                content=exception_outcome["message"]
            ))
            logger.error(f"Error creating Jira issue: {e}")
            logger.debug("Exception details:", exc_info=True)
        
        return state
    
    def _handle_evaluation(self, state: AgentState) -> AgentState:
        """Evaluate the created Jira issue."""
        import time
        import concurrent.futures
        
        self._refresh_application_services()

        jira_result = state.get("jira_result")
        
        # Skip evaluation if no result, not successful, or no evaluator
        if (
            not jira_result
            or not jira_result.get("success")
            or not self.jira_evaluation_port
            or not self.requirement_workflow_service
        ):
            skip_reason = []
            logger.debug(f"Skipping evaluation: no jira_result or evaluator")
            return state
        
        issue_key = jira_result["key"]
        logger.info(f"Starting evaluation for {issue_key}...")
        eval_start = time.time()
        
        try:
            def do_evaluation():
                return self.requirement_workflow_service.evaluate_issue(issue_key)
            
            # Run evaluation with 90 second timeout (LLM timeout is 60s + buffer)
            EVAL_TIMEOUT = 90
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_evaluation)
                try:
                    evaluation = future.result(timeout=EVAL_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Evaluation timed out for {issue_key}")
                    state["evaluation_result"] = {"error": f"Evaluation timed out after {EVAL_TIMEOUT}s"}
                    state["messages"].append(AIMessage(
                        content=f"⚠️ Maturity evaluation timed out. The Confluence page will be created without evaluation scores."
                    ))
                    return state
            
            elapsed = time.time() - eval_start
            
            if evaluation and 'error' not in evaluation:
                state["evaluation_result"] = evaluation
                eval_msg = self.requirement_workflow_service.format_evaluation_result(evaluation)
                state["messages"].append(AIMessage(content=eval_msg))
                logger.info(f"Evaluation completed for {issue_key}: {evaluation.get('overall_maturity_score', 'N/A')}/100 ({elapsed:.1f}s)")
            else:
                error_msg = evaluation.get('error', 'Unknown error') if evaluation else 'No result'
                state["evaluation_result"] = {"error": error_msg}
                logger.warning(f"Evaluation failed for {issue_key}: {error_msg}")
                state["messages"].append(AIMessage(
                    content=f"⚠️ Maturity evaluation failed: {error_msg}. The Confluence page will be created without evaluation scores."
                ))
                
        except Exception as e:
            state["evaluation_result"] = {"error": str(e)}
            logger.error(f"Evaluation error for {issue_key}: {e}")
        
        return state
    
    def _route_after_evaluation(self, state: AgentState) -> str:
        """Route after evaluation - decide if we should create Confluence page."""
        self._refresh_application_services()

        # Create Confluence page if tool is available and Jira was created successfully
        # Even if evaluation failed, we can still create the page with basic info
        # Check for both custom tool and MCP tool
        has_confluence_capability = self.confluence_page_port is not None
        
        if has_confluence_capability and state.get("jira_result", {}).get("success"):
            return "confluence_creation"
        return "end"
    
    def _handle_confluence_creation(self, state: AgentState) -> AgentState:
        """Create Confluence page for the Jira issue using MCP protocol with fallback."""
        if state.get("intent") == "confluence_creation":
            self._refresh_application_services()
            self._refresh_flow_services()

            if not self.confluence_creation_service:
                state["confluence_result"] = {
                    "success": False,
                    "error": "Confluence page creation is not configured.",
                }
                state["messages"].append(
                    AIMessage(content="Confluence page creation is not configured.")
                )
                return state

            result = self.confluence_creation_service.handle(
                user_input=state.get("user_input", ""),
                messages=list(state.get("messages", [])),
                conversation_history=list(state.get("conversation_history", [])),
            )
            state["confluence_result"] = result.get("confluence_result")
            state["messages"].append(AIMessage(content=result.get("message", "")))

            if (
                state.get("confluence_result", {}).get("success")
                and result.get("rag_document")
                and result.get("rag_metadata")
            ):
                self._ingest_to_rag(result["rag_document"], result["rag_metadata"])
            return state

        self._refresh_application_services()

        jira_result = state.get("jira_result", {})
        evaluation_result = state.get("evaluation_result", {})
        backlog_data = jira_result.get("backlog_data", {})
        
        if not jira_result.get("success"):
            state["messages"].append(AIMessage(
                content="⚠ Cannot create Confluence page: Jira issue was not created successfully."
            ))
            return state
        
        issue_key = jira_result["key"]
        tool_used = None
        
        try:
            logger.info(f"Creating Confluence page for {issue_key}...")
            page_title = f"{issue_key}: {backlog_data.get('summary', 'Untitled')}"

            if not self.requirement_workflow_service or not self.confluence_page_port:
                failure_outcome = build_confluence_failure_outcome(
                    confluence_result={"success": False, "error": "No Confluence port available"},
                    tool_used=None,
                    space_key=getattr(Config, 'CONFLUENCE_SPACE_KEY', 'the configured space'),
                )
                state["messages"].append(AIMessage(content=failure_outcome["message"]))
                return state

            confluence_result = self.requirement_workflow_service.create_confluence_page(
                issue_key=issue_key,
                backlog_data=backlog_data,
                evaluation_result=evaluation_result if evaluation_result else {},
                jira_link=jira_result["link"],
            )
            tool_used = confluence_result.get("tool_used")
            
            # Handle result
            if confluence_result.get("success"):
                import datetime as dt

                success_outcome = build_confluence_success_outcome(
                    confluence_result=confluence_result,
                    tool_used=tool_used,
                    page_title=page_title,
                    issue_key=issue_key,
                    created_at=dt.datetime.now().isoformat(),
                )
                state["confluence_result"] = confluence_result
                state["messages"].append(AIMessage(
                    content=success_outcome["message"]
                ))
                logger.info(f"Confluence page created: {confluence_result['link']}")
                
                # Ingest simplified Confluence content into RAG knowledge base
                # Use compact text version to reduce embedding API calls (1-2 chunks vs 5-10+)
                # Create simplified content for RAG (reduces from ~4000 chars to ~800 chars)
                simplified_content = self._simplify_for_rag(
                    issue_key=issue_key,
                    backlog_data=backlog_data,
                    evaluation=evaluation_result if evaluation_result else {},
                    confluence_link=confluence_result.get('link', '')
                )
                self._ingest_to_rag(simplified_content, success_outcome["metadata"])
            else:
                failure_outcome = build_confluence_failure_outcome(
                    confluence_result=confluence_result,
                    tool_used=tool_used,
                    space_key=getattr(Config, 'CONFLUENCE_SPACE_KEY', 'the configured space'),
                )
                
                state["messages"].append(AIMessage(content=failure_outcome["message"]))
                logger.error(
                    "Confluence page creation failed: %s (code: %s)",
                    failure_outcome["error"],
                    failure_outcome["error_code"],
                )
                
        except Exception as e:
            exception_outcome = build_confluence_exception_outcome(
                error_text=str(e),
                tool_used=tool_used,
                space_key=getattr(Config, 'CONFLUENCE_SPACE_KEY', 'the configured space'),
            )
            
            state["messages"].append(AIMessage(content=exception_outcome["message"]))
            logger.error(f"Error creating Confluence page: {e}")
            logger.debug("Exception details:", exc_info=True)
        
        logger.debug(f"Confluence creation completed for {issue_key}")
        return state
    
    def _handle_rag_query(self, state: AgentState) -> AgentState:
        """Handle RAG query - retrieve relevant context and answer."""
        self._refresh_flow_services()

        if not self.rag_query_service:
            state["messages"].append(
                AIMessage(
                    content=(
                        "I apologize, but the AI service is not configured correctly."
                    )
                )
            )
            return state

        result = self.rag_query_service.handle(
            user_input=state.get("user_input", ""),
            messages=state.get("messages", []),
        )
        state["messages"] = result["messages"]
        state["rag_context"] = result.get("rag_context")
        return state
    
    def _handle_coze_agent(self, state: AgentState) -> AgentState:
        """Handle Coze agent execution - route to Coze platform API."""
        self._refresh_flow_services()

        if not self.coze_agent_service:
            state["messages"].append(
                AIMessage(
                    content=(
                        "Coze agent is not properly configured. Please check your "
                        "COZE_API_TOKEN and COZE_BOT_ID settings."
                    )
                )
            )
            return state

        result = self.coze_agent_service.handle(
            user_input=state.get("user_input", ""),
            previous_result=state.get("coze_result"),
        )
        state["messages"].append(AIMessage(content=result["message"]))
        if result.get("coze_result") is not None:
            state["coze_result"] = result["coze_result"]
        return state
    
    def _html_to_markdown(self, html_content: str) -> str:
        """Delegate HTML-to-markdown conversion to the Atlassian support helper."""
        self._refresh_helper_services()
        return self.atlassian_support_service.html_to_markdown(html_content)
    
    def _simplify_for_rag(self, issue_key: str, backlog_data: Dict, 
                          evaluation: Dict, confluence_link: str) -> str:
        """Delegate compact Confluence formatting to the RAG ingestion helper."""
        self._refresh_helper_services()
        return self.rag_ingestion_service.simplify_confluence_content(
            issue_key=issue_key,
            backlog_data=backlog_data,
            evaluation=evaluation,
            confluence_link=confluence_link,
        )
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """
        Get LLM monitoring statistics.
        
        Returns:
            Dictionary with monitoring statistics (calls, tokens, duration, cost)
        """
        if hasattr(self, 'llm_callback'):
            return self.llm_callback.get_statistics()
        return {}
    
    def log_monitoring_summary(self):
        """Log a summary of LLM monitoring statistics."""
        if hasattr(self, 'llm_callback'):
            self.llm_callback.log_summary()
    
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
        
        # Run the graph (LangGraph execution) with timeout to prevent hanging
        logger.info("Processing input through agent graph...")
        final_state = None
        try:
            # Use timeout wrapper to prevent infinite hangs (300 seconds for Coze API which may take longer)
            # Also set recursion_limit to prevent infinite loops (10 should be more than enough)
            graph_config = {"recursion_limit": 10}
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.graph.invoke, initial_state, config=graph_config)
                try:
                    final_state = future.result(timeout=300.0)  # 300 second timeout (5 minutes) for Coze API
                except concurrent.futures.TimeoutError:
                    logger.error("Agent graph execution timed out after 300 seconds")
                    return "I apologize, but the request timed out after 5 minutes. Please try again with a simpler query."
        except Exception as e:
            logger.error(f"Error during graph execution: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}"
        
        # Check if we got a valid final state
        if not final_state:
            logger.error("Graph execution did not return a valid state")
            return "I apologize, but I couldn't process your request. Please try again."
        
        # Log the intent that was detected
        detected_intent = final_state.get("intent", "unknown")
        logger.info(f"Intent detected = '{detected_intent}'")
        
        # Log which nodes were executed
        if detected_intent == "jira_creation":
            logger.debug("Executed nodes: intent_detection → jira_creation → evaluation")
            if final_state.get("jira_result", {}).get("success"):
                logger.info(f"Jira issue created: {final_state.get('jira_result', {}).get('key', 'N/A')}")
        elif detected_intent == "rag_query":
            logger.debug("Executed nodes: intent_detection → rag_query")
        elif detected_intent == "general_chat":
            logger.debug("Executed nodes: intent_detection → general_chat")
        
        # Extract the last assistant message
        messages = final_state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage):
                logger.debug("Response generated successfully")
                return last_msg.content
        
        logger.warning("No response generated")
        return "I apologize, but I couldn't generate a response."


