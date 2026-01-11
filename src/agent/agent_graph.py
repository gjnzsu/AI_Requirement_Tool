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
import sys
import concurrent.futures
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.jira_tool import JiraTool
from src.tools.confluence_tool import ConfluenceTool
from src.services.jira_maturity_evaluator import JiraMaturityEvaluator
from src.services.coze_client import CozeClient
from src.services.intent_detector import IntentDetector
from src.mcp.mcp_integration import MCPIntegration
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
        """
        Get cloudId for Atlassian Rovo MCP Server.
        
        Tries multiple methods:
        1. MCP tool getAccessibleAtlassianResources
        2. Tenant info API endpoint (_edge/tenant_info)
        3. Extract from URL (if possible)
        
        Returns:
            cloudId string or None if not available
        """
        import json
        import re
        
        # Method 1: Try to get it from MCP tool getAccessibleAtlassianResources
        if self.use_mcp and self.mcp_integration and self.mcp_integration._initialized:
            try:
                resources_tool = self.mcp_integration.get_tool('getAccessibleAtlassianResources')
                if resources_tool:
                    try:
                        logger.info("Attempting to retrieve cloudId from getAccessibleAtlassianResources MCP tool...")
                        result = resources_tool.invoke(input={})
                        logger.debug(f"Response type: {type(result)}, length: {len(str(result)) if result else 0}")
                        
                        # Parse result to extract cloudId
                        if isinstance(result, str):
                            try:
                                # Clean up JSON if it's wrapped in code blocks
                                cleaned_result = result.strip()
                                if cleaned_result.startswith('```'):
                                    lines = cleaned_result.split('\n')
                                    json_lines = [line for line in lines if not line.strip().startswith('```')]
                                    cleaned_result = '\n'.join(json_lines)
                                
                                data = json.loads(cleaned_result)
                                logger.debug(f"Parsed JSON keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                                
                                if isinstance(data, dict):
                                    # Look for cloudId in the response
                                    if 'cloudId' in data:
                                        cloud_id = data['cloudId']
                                        logger.info(f"✓ Found cloudId in response: {cloud_id}")
                                        return cloud_id
                                    
                                    # Or check if it's a list of resources
                                    if 'resources' in data:
                                        resources = data['resources']
                                        if isinstance(resources, list) and len(resources) > 0:
                                            first_resource = resources[0]
                                            logger.debug(f"First resource keys: {list(first_resource.keys()) if isinstance(first_resource, dict) else 'not a dict'}")
                                            if isinstance(first_resource, dict) and 'cloudId' in first_resource:
                                                cloud_id = first_resource['cloudId']
                                                logger.info(f"✓ Found cloudId in first resource: {cloud_id}")
                                                return cloud_id
                                            # Also check for 'id' field which might be cloudId
                                            if isinstance(first_resource, dict) and 'id' in first_resource:
                                                cloud_id = first_resource['id']
                                                logger.info(f"✓ Found id in first resource (using as cloudId): {cloud_id}")
                                                return cloud_id
                                
                                # If it's a list directly
                                if isinstance(data, list) and len(data) > 0:
                                    first_item = data[0]
                                    if isinstance(first_item, dict):
                                        if 'cloudId' in first_item:
                                            cloud_id = first_item['cloudId']
                                            logger.info(f"✓ Found cloudId in list item: {cloud_id}")
                                            return cloud_id
                                            
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse JSON from getAccessibleAtlassianResources: {e}")
                                logger.debug(f"Raw result (first 200 chars): {str(result)[:200]}")
                    except Exception as e:
                        logger.warning(f"Exception calling getAccessibleAtlassianResources: {e}")
                        logger.debug("Exception details:", exc_info=True)
            except Exception as e:
                logger.warning(f"Exception getting getAccessibleAtlassianResources tool: {e}")
        
        # Method 2: Try to get it from tenant_info API endpoint
        jira_url = Config.JIRA_URL
        if jira_url and 'atlassian.net' in jira_url:
            try:
                # Extract base URL (e.g., https://yourcompany.atlassian.net)
                base_url = jira_url.split('/wiki')[0].split('/browse')[0].rstrip('/')
                tenant_info_url = f"{base_url}/_edge/tenant_info"
                
                logger.info(f"Attempting to fetch cloudId from tenant_info endpoint: {tenant_info_url}")
                
                import urllib.request
                import urllib.error
                
                # Create request with basic auth if credentials available
                req = urllib.request.Request(tenant_info_url)
                if Config.JIRA_EMAIL and Config.JIRA_API_TOKEN:
                    import base64
                    credentials = f"{Config.JIRA_EMAIL}:{Config.JIRA_API_TOKEN}"
                    encoded_credentials = base64.b64encode(credentials.encode()).decode()
                    req.add_header("Authorization", f"Basic {encoded_credentials}")
                
                req.add_header("Accept", "application/json")
                
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        if isinstance(data, dict) and 'cloudId' in data:
                            cloud_id = data['cloudId']
                            logger.info(f"✓ Retrieved cloudId from tenant_info endpoint: {cloud_id}")
                            return cloud_id
                except urllib.error.HTTPError as e:
                    logger.warning(f"HTTP error fetching tenant_info: {e.code} {e.reason}")
                except urllib.error.URLError as e:
                    logger.warning(f"URL error fetching tenant_info: {e.reason}")
                except Exception as e:
                    logger.warning(f"Exception fetching tenant_info: {e}")
                    
            except Exception as e:
                logger.warning(f"Exception constructing tenant_info URL: {e}")
        
        logger.warning("✗ Could not retrieve cloudId from any method (MCP tool and tenant_info endpoint both failed)")
        return None
    
    def _get_space_id(self, space_key: str, cloud_id: Optional[str] = None) -> Optional[int]:
        """
        Get numeric space ID from space key for Atlassian Rovo MCP Server.
        
        Tries multiple methods:
        1. MCP tool getConfluenceSpaces
        2. Direct Confluence API call
        
        Args:
            space_key: Space key (e.g., "SCRUM")
            cloud_id: Optional cloudId (if already retrieved)
            
        Returns:
            Space ID (int) or None if not available
        """
        import json
        import re
        
        if not space_key:
            return None
        
        # Method 1: Try to get it from MCP tool getConfluenceSpaces
        if self.use_mcp and self.mcp_integration and self.mcp_integration._initialized:
            try:
                spaces_tool = self.mcp_integration.get_tool('getConfluenceSpaces')
                if spaces_tool:
                    try:
                        logger.debug(f"Looking up space ID for space key '{space_key}' using getConfluenceSpaces...")
                        # Prepare arguments for getConfluenceSpaces
                        spaces_args = {}
                        if cloud_id:
                            spaces_args['cloudId'] = cloud_id
                        
                        result = spaces_tool.invoke(input=spaces_args)
                        logger.debug(f"getConfluenceSpaces response type: {type(result)}")
                        
                        # Parse result to find space ID
                        if isinstance(result, str):
                            try:
                                # Clean up JSON if it's wrapped in code blocks
                                cleaned_result = result.strip()
                                if cleaned_result.startswith('```'):
                                    lines = cleaned_result.split('\n')
                                    json_lines = [line for line in lines if not line.strip().startswith('```')]
                                    cleaned_result = '\n'.join(json_lines)
                                
                                data = json.loads(cleaned_result)
                                
                                if isinstance(data, dict):
                                    # Check if it's a list of spaces in 'results' or 'spaces'
                                    spaces_list = data.get('results', data.get('spaces', data.get('_results', [])))
                                    if not isinstance(spaces_list, list):
                                        # Maybe the data itself is a list
                                        if isinstance(data.get('data'), list):
                                            spaces_list = data['data']
                                    
                                    # Search for space with matching key
                                    for space in spaces_list:
                                        if isinstance(space, dict):
                                            # Check various possible field names for space key
                                            space_key_field = space.get('key') or space.get('spaceKey') or space.get('_expandable', {}).get('key')
                                            if space_key_field == space_key:
                                                # Extract space ID
                                                space_id = space.get('id') or space.get('spaceId')
                                                if space_id:
                                                    # Convert to int if it's a string
                                                    if isinstance(space_id, str):
                                                        # Extract numeric ID if it's in a format like "123456"
                                                        id_match = re.search(r'\d+', space_id)
                                                        if id_match:
                                                            space_id = int(id_match.group())
                                                    else:
                                                        space_id = int(space_id)
                                                    logger.info(f"Found space ID for '{space_key}': {space_id}")
                                                    return space_id
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse JSON from getConfluenceSpaces: {e}")
                                logger.debug(f"Raw result (first 200 chars): {str(result)[:200]}")
                    except Exception as e:
                        logger.warning(f"Exception calling getConfluenceSpaces: {e}")
            except Exception as e:
                logger.warning(f"Exception getting getConfluenceSpaces tool: {e}")
        
        # Method 2: Try to get it from direct Confluence API
        confluence_url = Config.CONFLUENCE_URL
        if confluence_url:
            try:
                import base64
                import urllib.request
                import urllib.error
                
                # Construct API URL
                base_url = confluence_url.split('/wiki')[0].rstrip('/')
                api_url = f"{base_url}/wiki/rest/api/space/{space_key}"
                
                logger.debug(f"Attempting to fetch space ID from Confluence API: {api_url}")
                
                # Prepare authentication
                email = Config.JIRA_EMAIL  # Confluence uses same credentials as Jira
                api_token = Config.JIRA_API_TOKEN
                credentials = f"{email}:{api_token}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                
                # Create request
                req = urllib.request.Request(api_url)
                req.add_header('Authorization', f'Basic {encoded_credentials}')
                req.add_header('Content-Type', 'application/json')
                
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        response_data = response.read().decode('utf-8')
                        space_data = json.loads(response_data)
                        
                        # Extract space ID
                        space_id = space_data.get('id')
                        if space_id:
                            # Convert to int if it's a string
                            if isinstance(space_id, str):
                                id_match = re.search(r'\d+', space_id)
                                if id_match:
                                    space_id = int(id_match.group())
                            else:
                                space_id = int(space_id)
                            logger.info(f"Retrieved space ID from API: {space_id}")
                            return space_id
                except urllib.error.HTTPError as e:
                    logger.warning(f"HTTP error fetching space info: {e.code} - {e.reason}")
                except urllib.error.URLError as e:
                    logger.warning(f"URL error fetching space info: {e.reason}")
                except Exception as e:
                    logger.warning(f"Exception fetching space info: {e}")
            except Exception as e:
                logger.warning(f"Exception constructing space API URL: {e}")
        
        logger.warning(f"Could not retrieve space ID for space key '{space_key}'")
        return None
    
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
        
        if self.enable_tools:
            self._initialize_tools()
        
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
        
        # Initialize intent detector (lazy initialization - will be created on first use)
        self.intent_detector: Optional[IntentDetector] = None
        
        # Initialize intent cache for avoiding redundant LLM calls
        self._intent_cache: Dict[str, Dict[str, Any]] = {}
        self._intent_cache_max_size = 100  # Cache last 100 detections
        
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
                    max_retries=2  # Increased retries for better reliability
                )
                logger.info(f"LLM initialized: {self.provider_name} ({model_name})")
                return llm
            except TypeError:
                # Fallback if parameters not supported
                logger.warning("LLM timeout parameter not supported, using default")
                return ChatOpenAI(
                    model=model_name,
                    temperature=self.temperature,
                    api_key=api_key
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
                    max_retries=2  # Limit retries to avoid long waits
                )
            except TypeError:
                # Fallback if parameters not supported
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=self.temperature,
                    google_api_key=api_key
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
                    max_retries=2  # Increased retries for better reliability
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
                    base_url="https://api.deepseek.com"
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
        graph.add_node("coze_agent", self._handle_coze_agent)
        
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
                "coze_agent": "coze_agent",
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
        
        # RAG, general chat, and Coze agent go directly to END
        graph.add_edge("rag_query", END)
        graph.add_edge("general_chat", END)
        graph.add_edge("coze_agent", END)
        
        return graph.compile()
    
    def _detect_intent(self, state: AgentState) -> AgentState:
        """Detect user intent from the input with comprehensive keyword-based detection."""
        user_input = state.get("user_input", "").lower()
        messages = state.get("messages", [])
        logger.debug(f"Detecting intent for input: '{user_input[:50]}...'")
        
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
        # These keywords trigger RAG to search through ingested documents
        rag_keywords = [
            # Documentation patterns
            'knowledge base', 'document', 'documentation', 'documents',
            'guide', 'guides', 'tutorial', 'tutorials',
            'example', 'examples', 'sample', 'samples',
            # Knowledge patterns
            'understand', 'understanding',
            'search', 'search for', 'look for', 'look up'
        ]
        
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
            logger.debug("Intent: general_chat (Confluence tooling query)")
            return state
        
        # Check for Coze agent intent keywords (AI daily report, AI news)
        coze_keywords = ['ai daily report', 'ai news']
        if any(keyword in user_input for keyword in coze_keywords):
            # Check if Coze is enabled and configured
            if Config.COZE_ENABLED:
                state["intent"] = "coze_agent"
                matched_keywords = [k for k in coze_keywords if k in user_input]
                logger.info(f"Intent: coze_agent (matched keywords: {matched_keywords})")
                return state
            else:
                logger.debug("Coze keyword detected but Coze is disabled - routing to general_chat")
        
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
                logger.debug("Intent: jira_creation (keyword match)")
                return state
        
        # Then try regex patterns for more complex phrases
        import re
        for pattern in jira_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                # Check if we have either custom tool or MCP tool available
                has_jira_capability = self.jira_tool or (self.use_mcp and self.mcp_integration)
                if has_jira_capability:
                    state["intent"] = "jira_creation"
                    logger.debug(f"Intent: jira_creation (pattern match: {pattern})")
                    return state
        
        # Check for RAG intent keywords (knowledge/documentation queries)
        # Use case-insensitive matching and check if any keyword appears in the input
        user_input_lower = user_input.lower()
        rag_keyword_found = any(keyword in user_input_lower for keyword in rag_keywords)
        
        # Also check if RAG service is available (if not, route to general_chat)
        if rag_keyword_found:
            # Check if RAG service is available
            rag_service_available = getattr(self, '_rag_service', None) is not None
            if rag_service_available:
                matched_keywords = [k for k in rag_keywords if k in user_input_lower]
                state["intent"] = "rag_query"
                logger.info(f"Intent: rag_query (matched keywords: {matched_keywords[:3]})")
                logger.debug(f"Full user input: {user_input[:100]}")
                return state
            else:
                logger.warning("RAG keyword detected but RAG service not available - RAG may be disabled or not initialized")
                logger.debug(f"Matched RAG keywords: {[k for k in rag_keywords if k in user_input_lower][:3]}")
                # Fall through to general_chat
        
        # Check for general chat keywords (simple questions, greetings)
        if any(keyword in user_input for keyword in general_chat_keywords):
            state["intent"] = "general_chat"
            logger.debug("Intent: general_chat (keyword match)")
            return state
        
        # No clear keyword match found - use LLM-based detection for ambiguous cases
        if Config.INTENT_USE_LLM:
            try:
                # Check cache first
                cached_result = self._get_cached_intent(user_input)
                if cached_result:
                    state["intent"] = cached_result.get("intent", "general_chat")
                    logger.debug(f"Intent: {state['intent']} (from cache)")
                    return state
                
                # Initialize intent detector if not already initialized
                intent_detector = self._initialize_intent_detector()
                if intent_detector:
                    # Prepare conversation context from recent messages
                    conversation_context = None
                    if messages and len(messages) > 0:
                        # Extract last few messages for context (skip system messages)
                        recent_messages = []
                        for msg in messages[-5:]:  # Last 5 messages
                            if isinstance(msg, HumanMessage):
                                recent_messages.append(f"User: {msg.content}")
                            elif isinstance(msg, AIMessage):
                                recent_messages.append(f"Assistant: {msg.content}")
                        if recent_messages:
                            conversation_context = recent_messages
                    
                    # Call LLM-based intent detection with timeout.
                    #
                    # IMPORTANT: do NOT use the ThreadPoolExecutor context manager here.
                    # If future.result(timeout=...) times out, the context manager's
                    # shutdown(wait=True) would still block until the worker finishes.
                    import concurrent.futures
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    future = executor.submit(
                        intent_detector.detect_intent,
                        user_input,
                        conversation_context
                    )
                    try:
                        llm_result = future.result(timeout=Config.INTENT_LLM_TIMEOUT)

                        # Validate confidence threshold
                        confidence = llm_result.get("confidence", 0.0)
                        if confidence >= Config.INTENT_CONFIDENCE_THRESHOLD:
                            detected_intent = llm_result.get("intent", "general_chat")
                            state["intent"] = detected_intent

                            # Cache the result
                            self._cache_intent(user_input, llm_result)

                            logger.info(
                                f"Intent: {detected_intent} (LLM detection, "
                                f"confidence: {confidence:.2f}, reasoning: {llm_result.get('reasoning', 'N/A')[:50]})"
                            )
                            return state
                        else:
                            logger.debug(
                                f"LLM confidence {confidence:.2f} below threshold "
                                f"{Config.INTENT_CONFIDENCE_THRESHOLD}, falling back to general_chat"
                            )
                    except concurrent.futures.TimeoutError:
                        # Best-effort cancellation; running threads can't be force-killed in CPython.
                        future.cancel()
                        logger.warning(
                            f"Intent detection timeout after {Config.INTENT_LLM_TIMEOUT}s, "
                            f"falling back to general_chat"
                        )
                    except Exception as e:
                        logger.warning(f"Error during LLM intent detection: {e}, falling back to general_chat")
                    finally:
                        # Never block on worker shutdown (prevents test/runtime hangs).
                        executor.shutdown(wait=False, cancel_futures=True)
                else:
                    logger.debug("Intent detector not available, falling back to general_chat")
            except Exception as e:
                logger.warning(f"Unexpected error in LLM intent detection: {e}, falling back to general_chat")
        
        # Fallback to general_chat if LLM detection fails or is disabled
        state["intent"] = "general_chat"
        logger.debug("Intent: general_chat (default fallback)")
        return state
    
    def _route_after_intent(self, state: AgentState) -> str:
        """Route to appropriate node based on detected intent."""
        intent = state.get("intent", "general_chat")
        
        # For general chat, RAG queries, and Coze agent, don't initialize MCP - it's not needed
        if intent in ["general_chat", "rag_query", "coze_agent"]:
            # For Coze agent, check if it's properly configured
            if intent == "coze_agent":
                if Config.COZE_ENABLED and self.coze_client and self.coze_client.is_configured():
                    return "coze_agent"
                else:
                    logger.warning("Coze agent intent detected but Coze is not properly configured - falling back to general_chat")
                    return "general_chat"
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
        # IMPORTANT: Only use Confluence-specific tools, never Jira tools
        mcp_tool_names = [
            # Official Rovo MCP Server (camelCase)
            'getConfluencePage', 'getConfluenceSpaces', 'getPagesInConfluenceSpace',
            # Community packages (snake_case)
            'get_confluence_page', 'confluence_get_page', 'get_page', 
            'confluence_page_get', 'read_confluence_page', 'confluence_read_page'
        ]
        mcp_tool = None
        
        for tool_name in mcp_tool_names:
            tool = self.mcp_integration.get_tool(tool_name)
            if tool:
                # VALIDATION: Ensure this is actually a Confluence tool, not a Jira tool
                tool_name_lower = tool.name.lower()
                if 'jira' in tool_name_lower or 'issue' in tool_name_lower:
                    logger.debug(f"Tool '{tool.name}' appears to be a Jira tool, skipping")
                    continue
                if 'confluence' in tool_name_lower or 'page' in tool_name_lower:
                    mcp_tool = tool
                    logger.info(f"Found MCP Confluence retrieval tool: {tool.name}")
                    break
        
        if not mcp_tool:
            return {'success': False, 'error': 'MCP Confluence retrieval tool not available'}
        
        try:
            logger.info("Retrieving Confluence page info via MCP Protocol")
            logger.debug(f"MCP Tool: {mcp_tool.name}")
            if page_id:
                logger.debug(f"Page ID: {page_id}")
            if page_title:
                logger.debug(f"Page Title: {page_title}")
            
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
                future = executor.submit(mcp_tool.invoke, input=mcp_args)
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
            logger.debug("Detected Confluence page query, attempting MCP retrieval...")
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
                logger.info("Retrieved Confluence page info via MCP Protocol")
            else:
                logger.warning(f"Could not retrieve Confluence page via MCP: {page_info.get('error', 'Unknown error')}")
        
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
            
            # Use longer timeout wrapper - should be longer than LLM's internal timeout
            # LLM timeout is 60s for OpenAI/DeepSeek, 30s for Gemini
            # Wrapper timeout should be longer to allow LLM to handle its own timeout gracefully
            timeout_value = 90.0 if self.provider_name in ["openai", "deepseek"] else 45.0
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self.llm.invoke, messages)
                try:
                    response = future.result(timeout=timeout_value)
                    elapsed = time.time() - start_time
                    logger.debug(f"LLM response received in {elapsed:.2f}s")
                    messages.append(response)
                    state["messages"] = messages
                except concurrent.futures.TimeoutError:
                    elapsed = time.time() - start_time
                    logger.warning(f"LLM response timeout ({elapsed:.2f}s) for {self.provider_name}")
                    logger.debug("Check: API key validity, network connection, model name")
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
                    logger.warning(f"LLM call error after {elapsed:.2f}s: {executor_error}")
                    logger.debug(f"Error type: {error_type}")
                    
                    # Check for HTTP status codes in error attributes
                    http_status_code = None
                    if hasattr(executor_error, 'status_code'):
                        http_status_code = executor_error.status_code
                    elif hasattr(executor_error, 'response') and hasattr(executor_error.response, 'status_code'):
                        http_status_code = executor_error.response.status_code
                    elif '429' in error_str or 'status code 429' in error_str:
                        http_status_code = 429
                    elif '401' in error_str or 'status code 401' in error_str:
                        http_status_code = 401
                    elif '403' in error_str or 'status code 403' in error_str:
                        http_status_code = 403
                    
                    # Detect error category by checking both type name and error message
                    is_connection_error = (
                        'Connection' in error_type or 
                        'connection' in error_str or
                        'connect' in error_str or
                        'network' in error_str or
                        'unreachable' in error_str or
                        'timeout' in error_str
                    ) and http_status_code is None
                    is_auth_error = (
                        http_status_code in [401, 403] or
                        'Authentication' in error_type or 
                        'auth' in error_str or 
                        'api key' in error_str or
                        'unauthorized' in error_str or
                        'invalid' in error_str and 'key' in error_str
                    )
                    is_rate_limit_error = (
                        http_status_code == 429 or
                        'RateLimit' in error_type or 
                        'rate limit' in error_str or
                        'rate_limit' in error_str or
                        'quota' in error_str or
                        '429' in error_str
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
                        # Don't log traceback for connection errors - they're common and expected
                        logger.debug("Connection error detected, providing user-friendly message")
                    elif is_auth_error:
                        user_message = (
                            "I apologize, but there's an authentication issue. "
                            "Please check that your API key is correctly configured and has the necessary permissions."
                        )
                        logger.debug("Authentication error detected")
                    elif is_rate_limit_error:
                        # Provide detailed, user-friendly rate limit message
                        provider_name = self.provider_name.capitalize() if self.provider_name else "API"
                        user_message = (
                            f"⚠️ Rate Limit Exceeded\n\n"
                            f"I apologize, but the {provider_name} API rate limit has been exceeded. "
                            f"This means you've made too many requests in a short period.\n\n"
                            f"**What you can do:**\n"
                            f"• Wait a few minutes and try again\n"
                            f"• Switch to a different model (OpenAI, DeepSeek) if available\n"
                            f"• Check your API quota/usage limits in your {provider_name} account\n\n"
                            f"Rate limits are temporary and will reset after a short waiting period."
                        )
                        logger.warning(f"Rate limit error detected (HTTP {http_status_code or 'N/A'}): {executor_error}")
                        logger.debug("Rate limit error detected")
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
            logger.error(f"Unexpected error in general chat: {e}")
            logger.debug(f"Error type: {error_type}")
            
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
        
        logger.info("Jira Creation: Checking available tools...")
        logger.debug(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Try to use MCP if enabled and available, otherwise fall back to custom tools
        use_mcp = self.use_mcp and self.mcp_integration is not None
        
        if self.use_mcp:
            logger.debug(f"MCP is enabled (USE_MCP={self.use_mcp})")
        else:
            logger.debug(f"MCP is disabled (USE_MCP={self.use_mcp})")
        
        # Initialize MCP if needed (lazy initialization)
        if use_mcp and not self.mcp_integration._initialized:
            logger.info("Initializing MCP integration (lazy initialization)...")
            try:
                import asyncio
                asyncio.run(self.mcp_integration.initialize())
                logger.info("MCP integration initialized successfully")
            except Exception as e:
                logger.warning(f"MCP initialization failed: {e}")
                logger.info("Falling back to custom tools")
                use_mcp = False
        
        # Check if we have MCP tools available
        # IMPORTANT: Only use Jira-specific tools, never Confluence tools for Jira operations
        mcp_jira_tool = None
        if use_mcp:
            # Try to get Jira tool by exact name first
            jira_tool_names = ['create_jira_issue', 'createJiraIssue', 'createIssue']
            for tool_name in jira_tool_names:
                tool = self.mcp_integration.get_tool(tool_name)
                if tool:
                    # Verify it's actually a Jira tool, not a Confluence tool
                    tool_name_lower = tool.name.lower()
                    if 'confluence' in tool_name_lower or 'page' in tool_name_lower:
                        logger.debug(f"Tool '{tool.name}' appears to be a Confluence tool, skipping")
                        continue
                    if 'jira' in tool_name_lower or 'issue' in tool_name_lower:
                        mcp_jira_tool = tool
                        logger.info(f"Found Jira MCP tool: {tool.name}")
                        break
            
            if not mcp_jira_tool:
                # Fallback: search all tools but explicitly exclude Confluence tools
                all_tools = self.mcp_integration.get_tools()
                for tool in all_tools:
                    tool_name_lower = tool.name.lower()
                    # Explicitly exclude Confluence tools
                    if 'confluence' in tool_name_lower or 'page' in tool_name_lower:
                        continue
                    # Only accept tools that are clearly Jira-related
                    if ('jira' in tool_name_lower or 'issue' in tool_name_lower) and 'create' in tool_name_lower:
                        mcp_jira_tool = tool
                        logger.info(f"Found Jira MCP tool by pattern: {tool.name}")
                        break
                
                if not mcp_jira_tool:
                    logger.warning("MCP tool 'create_jira_issue' not available, using custom tool")
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
            # VALIDATION: Ensure we're using a Jira tool, not a Confluence tool
            if use_mcp and mcp_jira_tool:
                # Final safety check: verify this is actually a Jira tool
                tool_name_lower = mcp_jira_tool.name.lower()
                if 'confluence' in tool_name_lower or ('page' in tool_name_lower and 'jira' not in tool_name_lower):
                    logger.warning(f"SAFETY CHECK FAILED: Tool '{mcp_jira_tool.name}' appears to be a Confluence tool!")
                    logger.info("Falling back to custom Jira tool")
                    mcp_jira_tool = None
                    use_mcp = False
            
            if use_mcp and mcp_jira_tool:
                tool_used = "MCP Tool"
                logger.info("Creating Jira issue via MCP tool...")
                logger.debug(f"Summary: {backlog_data.get('summary', 'Untitled Issue')[:50]}...")
                logger.debug(f"Priority: {backlog_data.get('priority', 'Medium')}")
                
                try:
                    # Call MCP tool with additional timeout wrapper for safety
                    import time
                    start_time = time.time()
                    
                    # Call MCP tool using synchronous invoke method with timeout
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            mcp_jira_tool.invoke,
                            input={
                                'summary': backlog_data.get('summary', 'Untitled Issue'),
                                'description': backlog_data.get('description', ''),
                                'priority': backlog_data.get('priority', 'Medium'),
                                'issue_type': backlog_data.get('issue_type', 'Story')
                            }
                        )
                        try:
                            mcp_result = future.result(timeout=75.0)  # 75 second timeout (MCP has 60s internal, add buffer)
                            elapsed = time.time() - start_time
                            logger.debug(f"MCP tool call completed in {elapsed:.2f}s")
                        except concurrent.futures.TimeoutError:
                            elapsed = time.time() - start_time
                            logger.warning(f"MCP tool call timed out after {elapsed:.2f}s")
                            logger.info("Falling back to custom tool")
                            tool_used = "Custom Tool (MCP timeout fallback)"
                            result = self.jira_tool.create_issue(
                                summary=backlog_data.get('summary', 'Untitled Issue'),
                                description=backlog_data.get('description', ''),
                                priority=backlog_data.get('priority', 'Medium')
                            )
                            if result.get('success'):
                                logger.info(f"Created issue {result.get('key', 'N/A')} via custom tool (MCP timeout)")
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
                                    logger.warning(f"MCP tool returned timeout error: {mcp_result}")
                                    raise Exception(f"MCP tool timeout: {mcp_result}")
                                if mcp_result.strip().startswith('Error:'):
                                    error_msg = mcp_result.replace('Error:', '').strip()
                                    logger.warning(f"MCP tool returned error: {error_msg}")
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
                                logger.info(f"Created issue {result['key']} via MCP tool")
                            else:
                                error_msg = mcp_data.get('error', 'Unknown error') if mcp_data else 'Invalid response'
                                logger.error(f"MCP Tool failed: {error_msg}")
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
                                logger.warning(f"MCP Tool returned error message: {mcp_result[:200]}")
                                # Fall back to custom tool
                                tool_used = "Custom Tool (MCP parse error fallback)"
                                result = self.jira_tool.create_issue(
                                    summary=backlog_data.get('summary', 'Untitled Issue'),
                                    description=backlog_data.get('description', ''),
                                    priority=backlog_data.get('priority', 'Medium')
                                )
                            else:
                                logger.error("MCP Tool failed: Invalid response format")
                                result = {'success': False, 'error': f'Invalid response format: {str(mcp_result)[:200]}'}
                except Exception as e:
                    error_str = str(e).lower()
                    if 'timeout' in error_str or 'timed out' in error_str:
                        logger.warning(f"MCP tool call timed out: {e}")
                        logger.info("Falling back to custom tool")
                    else:
                        logger.error(f"MCP tool call failed: {e}")
                        logger.info("Falling back to custom tool")
                        logger.debug("Exception details:", exc_info=True)
                    
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
                                logger.info(f"Created issue {result.get('key', 'N/A')} via custom tool (fallback)")
                        except Exception as fallback_error:
                            logger.error(f"Custom tool also failed: {fallback_error}")
                            result = {'success': False, 'error': f'MCP tool failed: {str(e)}. Custom tool also failed: {str(fallback_error)}'}
            else:
                # Use custom tool
                logger.info("Using Custom JiraTool to create Jira issue...")
                logger.debug(f"Summary: {backlog_data.get('summary', 'Untitled Issue')[:50]}...")
                logger.debug(f"Priority: {backlog_data.get('priority', 'Medium')}")
                result = self.jira_tool.create_issue(
                    summary=backlog_data.get('summary', 'Untitled Issue'),
                    description=backlog_data.get('description', ''),
                    priority=backlog_data.get('priority', 'Medium')
                )
                if result.get('success'):
                    logger.info(f"Custom Tool SUCCESS: Created issue {result.get('key', 'N/A')}")
                else:
                    logger.error(f"Custom Tool FAILED: {result.get('error', 'Unknown error')}")
            
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
                    # User-friendly error message without raw error details
                    user_message = (
                        "⚠ **Failed to create Jira issue:**\n\n"
                        "The system attempted to create the Jira issue but encountered an issue.\n\n"
                        "**Please check:**\n"
                        "- ✅ Your Jira configuration (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)\n"
                        "- ✅ API token has write permissions\n"
                        "- ✅ Network connectivity to Jira\n"
                        "- ✅ Jira project key is correct\n\n"
                        "Please try again or create the issue manually in Jira."
                    )
                
                state["messages"].append(AIMessage(content=user_message))
        except Exception as e:
            error_msg = f"Error creating Jira issue: {str(e)}"
            state["jira_result"] = {"success": False, "error": error_msg}
            
            # Provide user-friendly error message
            error_str = str(e).lower()
            if 'timeout' in error_str or 'timed out' in error_str:
                user_message = (
                    "⚠ **Jira issue creation failed:**\n\n"
                    "The request timed out. This may happen when:\n"
                    "- The Jira server is slow or overloaded\n"
                    "- There are network connectivity issues\n\n"
                    "**What you can do:**\n"
                    "- ✅ Try again in a few moments\n"
                    "- ✅ Check your network connection\n"
                    "- ✅ Create the issue manually in Jira if urgent\n"
                )
            else:
                # Generic error message - don't show raw error to user
                user_message = (
                    "⚠ **Jira issue creation failed:**\n\n"
                    "An unexpected error occurred while creating the Jira issue.\n\n"
                    "**What you can do:**\n"
                    "- ✅ Try again in a few moments\n"
                    "- ✅ Check your Jira configuration (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)\n"
                    "- ✅ Verify your API token has write permissions\n"
                    "- ✅ Create the issue manually in Jira if needed\n"
                )
            
            state["messages"].append(AIMessage(content=user_message))
            logger.error(f"Error creating Jira issue: {e}")
            logger.debug("Exception details:", exc_info=True)
        
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
            logger.error(f"Error during evaluation: {e}")
        
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
            logger.info(f"Creating Confluence page for {issue_key}...")
            
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
                    logger.info("Initializing MCP integration for Confluence...")
                    try:
                        import asyncio
                        import concurrent.futures
                        # Initialize with timeout to prevent blocking
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.mcp_integration.initialize())
                            try:
                                future.result(timeout=15.0)  # 15 second timeout for initialization
                                logger.info("MCP integration initialized for Confluence")
                            except concurrent.futures.TimeoutError:
                                logger.warning("MCP initialization timeout (15s) for Confluence")
                                use_mcp = False
                    except Exception as e:
                        logger.warning(f"MCP initialization failed: {e}")
                        use_mcp = False
                
                # Try to get MCP Confluence tool
                if use_mcp:
                    # Only get tools if MCP is initialized (don't trigger initialization here)
                    if self.mcp_integration._initialized:
                        all_tools = self.mcp_integration.get_tools()
                        logger.debug(f"Available MCP tools: {[tool.name for tool in all_tools]}")
                    else:
                        logger.debug("MCP not initialized yet, skipping tool discovery")
                        all_tools = []
                    
                    # Look for Confluence tools - check both exact names and patterns
                    mcp_confluence_tool = None
                    confluence_tool_candidates = []
                    
                    # Common MCP tool names for Confluence page creation (including Rovo server names)
                    # Official Rovo uses camelCase, community packages use snake_case
                    tool_name_patterns = [
                        # Official Rovo MCP Server (camelCase)
                        'createConfluencePage', 'getConfluencePage', 'updateConfluencePage',
                        'getConfluenceSpaces', 'getPagesInConfluenceSpace',
                        'getConfluencePageAncestors', 'getConfluencePageDescendants',
                        'createConfluenceFooterComment', 'createConfluenceInlineComment',
                        'getConfluencePageFooterComments', 'getConfluencePageInlineComments',
                        'searchConfluenceUsingCql',
                        # Community packages (snake_case)
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
                            logger.debug(f"Found potential Confluence tool: {tool_name}")
                    
                    # If no exact match, search through all tools for Confluence-related ones
                    if not confluence_tool_candidates:
                        for tool in all_tools:
                            tool_name_lower = tool.name.lower()
                            tool_name = tool.name
                            
                            # STRICT EXCLUSION: Explicitly exclude Jira tools
                            if 'jira' in tool_name_lower or 'issue' in tool_name_lower:
                                continue
                            
                            # Also exclude tools that might be ambiguous
                            # Check for common Jira-related keywords
                            jira_keywords = ['ticket', 'bug', 'story', 'task', 'epic', 'sprint']
                            if any(keyword in tool_name_lower for keyword in jira_keywords):
                                # Only exclude if it doesn't also contain Confluence keywords
                                if 'confluence' not in tool_name_lower:
                                    continue
                            
                            # Check if tool name matches Confluence patterns
                            # Official Rovo tools use camelCase (e.g., createConfluencePage)
                            is_official_rovo = (
                                'confluence' in tool_name and 
                                ('create' in tool_name or 'get' in tool_name or 'update' in tool_name or 
                                 'search' in tool_name or 'page' in tool_name or 'space' in tool_name or
                                 'comment' in tool_name)
                            )
                            
                            # Community package tools use snake_case or lowercase
                            is_confluence_tool = (
                                'confluence' in tool_name_lower or
                                ('rovo' in tool_name_lower and ('page' in tool_name_lower or 'create' in tool_name_lower)) or
                                ('page' in tool_name_lower and 'create' in tool_name_lower and 'jira' not in tool_name_lower)
                            )
                            
                            if is_official_rovo or is_confluence_tool:
                                # Final validation: ensure it's not a Jira tool
                                if 'jira' not in tool_name_lower and 'issue' not in tool_name_lower:
                                    confluence_tool_candidates.append((tool.name, tool))
                                    logger.debug(f"Found potential Confluence tool by pattern: {tool.name}")
                    
                    # Use the first candidate found
                    if confluence_tool_candidates:
                        tool_name, mcp_confluence_tool = confluence_tool_candidates[0]
                        logger.info(f"Selected MCP Confluence tool: {tool_name}")
                    else:
                        logger.warning("No Confluence MCP tools found")
                        logger.debug(f"Available tools: {[tool.name for tool in all_tools]}")
                        logger.debug("This may indicate the Confluence MCP server timed out or isn't configured")
                        mcp_confluence_tool = None
                    
                    if mcp_confluence_tool:
                        # VALIDATION: Final safety check to ensure this is actually a Confluence tool
                        tool_name_lower = mcp_confluence_tool.name.lower()
                        if 'jira' in tool_name_lower or 'issue' in tool_name_lower:
                            logger.warning(f"SAFETY CHECK FAILED: Tool '{mcp_confluence_tool.name}' appears to be a Jira tool!")
                            logger.info("Falling back to direct Confluence API")
                            mcp_confluence_tool = None
                            use_mcp = False
                        
                        if mcp_confluence_tool:
                            logger.info("Creating Confluence page via MCP tool...")
                            logger.debug(f"MCP Tool: {mcp_confluence_tool.name}")
                            logger.debug(f"Title: {page_title}")
                            tool_used = "MCP Protocol"
                            
                            try:
                                # Call MCP tool with timeout
                                import asyncio
                                import concurrent.futures
                                
                                # Get tool schema to determine correct parameter names
                                tool_schema = None
                                if hasattr(mcp_confluence_tool, '_tool_schema'):
                                    tool_schema = mcp_confluence_tool._tool_schema
                                elif hasattr(mcp_confluence_tool, 'args_schema') and mcp_confluence_tool.args_schema:
                                    # Extract schema from Pydantic model
                                    tool_schema = {'inputSchema': {'properties': {}}}
                                    if hasattr(mcp_confluence_tool.args_schema, 'model_fields'):
                                        for field_name, field_info in mcp_confluence_tool.args_schema.model_fields.items():
                                            tool_schema['inputSchema']['properties'][field_name] = {
                                                'type': 'string',  # Default, could be improved
                                                'description': field_info.description if hasattr(field_info, 'description') else ''
                                            }
                                
                                # Prepare arguments based on tool schema
                                mcp_args = {}
                                
                                # Check if this is a Rovo tool (camelCase naming) - these require cloudId
                                is_rovo_tool = any(char.isupper() for char in mcp_confluence_tool.name) and 'Confluence' in mcp_confluence_tool.name
                                
                                # Get cloudId early if this is a Rovo tool
                                cloud_id = None
                                if is_rovo_tool:
                                    logger.info("Detected Rovo tool - retrieving cloudId...")
                                    cloud_id = self._get_cloud_id()
                                    if cloud_id:
                                        logger.info(f"✓ cloudId successfully retrieved: {cloud_id}")
                                    else:
                                        logger.warning("✗ cloudId not available - tool call may fail")
                                
                                # Check what parameters the tool expects
                                if tool_schema and 'inputSchema' in tool_schema:
                                    input_schema = tool_schema['inputSchema']
                                    properties = input_schema.get('properties', {})
                                    required = input_schema.get('required', [])
                                    
                                    # Map our data to the tool's expected parameters
                                    # Common parameter name mappings
                                    param_mapping = {
                                        'title': ['title', 'name', 'pageTitle', 'page_title'],
                                        'content': ['content', 'body', 'html', 'text', 'description'],
                                        'space': ['space', 'spaceKey', 'space_key', 'spaceId', 'space_id']
                                    }
                                    
                                    # Extract contentFormat enum values if available
                                    content_format_enum = None
                                    content_format_param = None
                                    for param_name in properties.keys():
                                        param_lower = param_name.lower()
                                        if 'contentformat' in param_lower or param_name == 'contentFormat':
                                            content_format_param = param_name
                                            param_def = properties[param_name]
                                            # Check for enum values
                                            if 'enum' in param_def:
                                                content_format_enum = param_def['enum']
                                            elif 'anyOf' in param_def:
                                                # Check anyOf for enum
                                                for any_of_item in param_def['anyOf']:
                                                    if 'enum' in any_of_item:
                                                        content_format_enum = any_of_item['enum']
                                                        break
                                            break
                                    
                                    # Try to match tool parameters to our data
                                    for param_name in properties.keys():
                                        param_lower = param_name.lower()
                                        
                                        # Map cloudId parameter FIRST (required for Rovo MCP Server)
                                        if 'cloudid' in param_lower or param_name == 'cloudId':
                                            if cloud_id:
                                                mcp_args[param_name] = cloud_id
                                                logger.info(f"✓ Mapped cloudId to parameter '{param_name}': {cloud_id}")
                                            # If cloudId is required but not available, we'll handle it in the required params check
                                        # Map contentFormat parameter BEFORE content (to avoid matching 'content' in 'contentFormat')
                                        elif 'contentformat' in param_lower or param_name == 'contentFormat':
                                            # Rovo MCP Server expects contentFormat - check schema for valid enum values
                                            # Default to "markdown" for Rovo tools if enum not specified
                                            if content_format_enum:
                                                # Use first enum value (usually "markdown" for Rovo)
                                                mcp_args[param_name] = content_format_enum[0]
                                                logger.debug(f"Using contentFormat from schema enum: {content_format_enum[0]}")
                                            else:
                                                # Default to "markdown" for Rovo MCP Server
                                                mcp_args[param_name] = "markdown"
                                                logger.debug("Using default contentFormat: markdown")
                                        # Map title/name parameters
                                        elif any(mapped in param_lower for mapped in ['title', 'name', 'pagetitle']):
                                            mcp_args[param_name] = page_title
                                        # Map content/body/description parameters (check AFTER contentFormat)
                                        elif any(mapped in param_lower for mapped in ['content', 'body', 'html', 'text', 'description']):
                                            # If contentFormat is markdown, convert HTML to markdown
                                            content_format_value = mcp_args.get(content_format_param if content_format_param else 'contentFormat', '')
                                            if content_format_value == 'markdown':
                                                # Convert HTML to markdown for Rovo MCP Server
                                                body_content = self._html_to_markdown(confluence_content)
                                                mcp_args[param_name] = body_content
                                                logger.debug(f"Converted HTML content to markdown (length: {len(body_content)} chars)")
                                            else:
                                                mcp_args[param_name] = confluence_content
                                        # Map space parameters
                                        elif any(mapped in param_lower for mapped in ['space', 'spacekey', 'spaceid']):
                                            # Check if parameter expects numeric ID (spaceId) vs string key (spaceKey)
                                            param_def = properties.get(param_name, {})
                                            param_type = param_def.get('type', '')
                                            
                                            # Rovo MCP Server uses spaceId - check schema to see if it expects string or number
                                            if 'spaceid' in param_lower or param_name == 'spaceId':
                                                # Check the expected type from schema
                                                expected_type = param_def.get('type', '')
                                                # Rovo MCP Server expects spaceId as a string (even though API uses numeric ID)
                                                space_key = Config.CONFLUENCE_SPACE_KEY
                                                space_id = self._get_space_id(space_key, cloud_id)
                                                if space_id:
                                                    # Convert to string as Pydantic validation expects string type
                                                    mcp_args[param_name] = str(space_id)
                                                    logger.debug(f"Converted space key '{space_key}' to space ID (as string): {mcp_args[param_name]}")
                                                else:
                                                    # Fallback: try to use space key as-is (might fail, but we'll try)
                                                    logger.warning(f"Could not get space ID for '{space_key}', using space key as-is (may fail)")
                                                    mcp_args[param_name] = space_key
                                            else:
                                                # Use string space key (spaceKey, space_key, etc.)
                                                mcp_args[param_name] = Config.CONFLUENCE_SPACE_KEY
                                    
                                    # Ensure all required parameters are provided
                                    for req_param in required:
                                        if req_param not in mcp_args:
                                            # Try to provide a default or raise an error
                                            if 'title' in req_param.lower() or 'name' in req_param.lower():
                                                mcp_args[req_param] = page_title
                                            elif 'content' in req_param.lower() or 'body' in req_param.lower() or 'description' in req_param.lower():
                                                # If contentFormat is markdown, convert HTML to markdown
                                                content_format_value = mcp_args.get(content_format_param if content_format_param else 'contentFormat', '')
                                                if content_format_value == 'markdown':
                                                    body_content = self._html_to_markdown(confluence_content)
                                                    mcp_args[req_param] = body_content
                                                    logger.debug(f"Converted HTML content to markdown for required param {req_param}")
                                                else:
                                                    mcp_args[req_param] = confluence_content
                                            elif 'space' in req_param.lower():
                                                # Check if it's spaceId (string representation of numeric ID) or spaceKey (string)
                                                if 'spaceid' in req_param.lower() or req_param == 'spaceId':
                                                    # Rovo MCP Server expects spaceId as a string (even though it represents a numeric ID)
                                                    space_key = Config.CONFLUENCE_SPACE_KEY
                                                    space_id = self._get_space_id(space_key, cloud_id)
                                                    if space_id:
                                                        # Convert to string as Pydantic validation expects string type
                                                        mcp_args[req_param] = str(space_id)
                                                        logger.debug(f"Converted space key '{space_key}' to space ID (as string) for required param {req_param}: {mcp_args[req_param]}")
                                                    else:
                                                        # Fallback: try to use space key as-is (might fail, but we'll try)
                                                        logger.warning(f"Could not get space ID for '{space_key}', using space key as-is for {req_param} (may fail)")
                                                        mcp_args[req_param] = space_key
                                                else:
                                                    # Use string space key
                                                    mcp_args[req_param] = Config.CONFLUENCE_SPACE_KEY
                                            elif 'cloudid' in req_param.lower() or req_param == 'cloudId':
                                                # Use cloudId that was already retrieved (if available)
                                                if cloud_id:
                                                    mcp_args[req_param] = cloud_id
                                                    logger.info(f"✓ Using cloudId in tool parameter '{req_param}': {cloud_id}")
                                                else:
                                                    # cloudId is required but not available
                                                    logger.warning("✗ cloudId required but not available. Tool call will fail, will fallback to direct API.")
                                                    # Don't add empty cloudId - let it fail and fallback gracefully
                                                    # This will cause the tool call to fail validation, triggering fallback
                                            elif 'contentformat' in req_param.lower() or req_param == 'contentFormat':
                                                # contentFormat is required for Rovo MCP Server
                                                # Default to "markdown" (Rovo MCP Server expects markdown, not storage)
                                                mcp_args[req_param] = "markdown"
                                                logger.debug("Added contentFormat: markdown")
                                else:
                                    # Fallback: try common parameter name variations
                                    mcp_args = {
                                        'title': page_title,
                                        'content': confluence_content,
                                        'space_key': Config.CONFLUENCE_SPACE_KEY,
                                        'spaceKey': Config.CONFLUENCE_SPACE_KEY,  # camelCase variant
                                        'space': Config.CONFLUENCE_SPACE_KEY,
                                        'spaceId': Config.CONFLUENCE_SPACE_KEY,  # Rovo uses spaceId (will be converted to numeric ID if needed)
                                        'body': confluence_content,  # Some servers use 'body' instead of 'content'
                                        'html': confluence_content,  # Some servers expect HTML
                                        'text': confluence_content,  # Some servers expect plain text
                                        'summary': page_title,  # Some tools use 'summary' instead of 'title'
                                        'description': confluence_content,  # Some tools use 'description' instead of 'content'
                                        'contentFormat': 'markdown'  # Rovo MCP Server requires contentFormat (markdown, not storage)
                                    }
                                    # Add cloudId if available
                                    if cloud_id:
                                        mcp_args['cloudId'] = cloud_id
                                        logger.info(f"✓ Added cloudId to tool arguments: {cloud_id}")
                                
                                # Log the tool being used and arguments
                                logger.debug(f"Tool Name: {mcp_confluence_tool.name}")
                                if tool_schema:
                                    logger.debug(f"Tool Schema: {list(mcp_args.keys())}")
                                logger.debug(f"Arguments: {', '.join([f'{k}=' + (str(v)[:30] + '...' if len(str(v)) > 30 else str(v)) for k, v in list(mcp_args.items())[:3]])}")
                                
                                # Try calling MCP tool with timeout
                                # StructuredTool.invoke expects input as keyword argument
                                # Using input= explicitly to match BaseTool/StructuredTool signature
                                logger.debug(f"Calling tool with arguments: {list(mcp_args.keys())}")
                                logger.debug(f"Tool object type: {type(mcp_confluence_tool)}")
                                logger.debug(f"Tool has invoke method: {hasattr(mcp_confluence_tool, 'invoke')}")
                                
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    try:
                                        logger.debug("Submitting tool.invoke(...) to executor...")
                                        # LangChain StructuredTool requires invoke(input={...}) with 'input' keyword
                                        future = executor.submit(mcp_confluence_tool.invoke, input=mcp_args)
                                        logger.debug("Waiting for tool result (timeout: 60s)...")
                                        mcp_result = future.result(timeout=60.0)  # 60 second timeout for Confluence operations
                                        logger.debug(f"Tool call completed, result type: {type(mcp_result)}")
                                        
                                        # Log raw result for debugging
                                        logger.debug(f"MCP tool raw result type: {type(mcp_result)}")
                                        if isinstance(mcp_result, str):
                                            logger.debug(f"MCP tool raw result (full length: {len(mcp_result)} chars)")
                                            logger.debug(f"First 1000 chars: {mcp_result[:1000]}")
                                            if len(mcp_result) > 1000:
                                                logger.debug(f"... (truncated, total {len(mcp_result)} chars)")
                                        elif isinstance(mcp_result, dict):
                                            logger.debug(f"MCP tool raw result keys: {list(mcp_result.keys())}")
                                            logger.debug(f"MCP tool raw result: {mcp_result}")
                                        else:
                                            logger.debug(f"MCP tool raw result: {repr(mcp_result)[:500]}")
                                        
                                        # Parse MCP result
                                        mcp_data = None
                                        if mcp_result is None:
                                            # Timeout or no result - skip processing, will fall back to direct API
                                            logger.debug("MCP result is None, skipping processing")
                                            tool_used = None
                                            use_mcp = False
                                        elif isinstance(mcp_result, str):
                                            # Try to parse as JSON
                                            import json
                                            import re
                                            
                                            # Clean the string - remove markdown code blocks, extra whitespace
                                            cleaned_result = mcp_result.strip()
                                            if cleaned_result.startswith('```'):
                                                # Extract JSON from code block
                                                lines = cleaned_result.split('\n')
                                                json_lines = [line for line in lines 
                                                             if not line.strip().startswith('```')]
                                                cleaned_result = '\n'.join(json_lines).strip()
                                            
                                            # Try parsing the full cleaned result directly first
                                            # The regex extraction can incorrectly match nested objects
                                            try:
                                                mcp_data = json.loads(cleaned_result)
                                                logger.debug("Successfully parsed JSON from MCP result")
                                                
                                                # Log the full parsed data structure for debugging
                                                if isinstance(mcp_data, dict):
                                                    logger.debug(f"Parsed JSON top-level keys: {list(mcp_data.keys())[:10]}")
                                                    # Check if we have the expected page structure
                                                    if 'id' in mcp_data:
                                                        logger.debug(f"Found page ID in root: {mcp_data.get('id')}")
                                                    elif 'version' in mcp_data:
                                                        logger.debug("WARNING: Only found 'version' key - might indicate parsing issue")
                                            except json.JSONDecodeError as first_parse_err:
                                                # If direct parse fails, try regex extraction as fallback
                                                logger.debug(f"Direct JSON parse failed: {first_parse_err}")
                                                logger.debug("Attempting regex extraction as fallback...")
                                                
                                                # Try to extract JSON object from the string (in case it's embedded in text)
                                                # Use a more robust pattern that matches balanced braces
                                                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_result, re.DOTALL)
                                                if json_match:
                                                    try:
                                                        cleaned_result = json_match.group(0)
                                                        mcp_data = json.loads(cleaned_result)
                                                        logger.debug("Successfully parsed JSON using regex extraction")
                                                    except json.JSONDecodeError:
                                                        # Regex extraction also failed
                                                        pass
                                            except json.JSONDecodeError as json_err:
                                                # If not JSON, check if it contains success indicators or page info
                                                logger.debug(f"JSON decode error: {json_err}")
                                                logger.debug("Attempting to parse as plain text response")
                                                
                                                # Check for explicit error indicators first
                                                # MCPToolWrapper returns "Error: ..." for errors
                                                if cleaned_result.strip().startswith('Error:'):
                                                    error_msg = cleaned_result[:500] if len(cleaned_result) > 500 else cleaned_result
                                                    raise Exception(f"MCP tool returned error: {error_msg}")
                                                
                                                # Check for other error indicators
                                                error_keywords = ['failed', 'invalid', 'unauthorized', 'forbidden', 'not found', '404', '500']
                                                has_error = any(keyword in cleaned_result.lower() for keyword in error_keywords)
                                                
                                                if has_error and 'success' not in cleaned_result.lower() and 'created' not in cleaned_result.lower():
                                                    error_msg = cleaned_result[:500] if len(cleaned_result) > 500 else cleaned_result
                                                    raise Exception(f"MCP tool returned error message: {error_msg}")
                                                
                                                # If not an error, try to extract success information
                                                # Try to extract page ID from the text
                                                page_id_match = re.search(r'(?:page[_\s]?id|pageId|id)[\s:=]+(\d+)', cleaned_result, re.IGNORECASE)
                                                page_id = page_id_match.group(1) if page_id_match else None
                                                
                                                # Try to extract URL (common in Confluence responses)
                                                url_match = re.search(r'https?://[^\s\)]+', cleaned_result)
                                                page_url = url_match.group(0) if url_match else None
                                                
                                                # If we have success indicators, page ID, or URL, treat as success
                                                # Also, if the tool completed without error (no "Error:" prefix), 
                                                # and it's not an obvious error, assume success
                                                has_success_indicators = (
                                                    'created' in cleaned_result.lower() or 
                                                    'success' in cleaned_result.lower() or
                                                    page_id or
                                                    page_url or
                                                    'confluence' in cleaned_result.lower()
                                                )
                                                
                                                if has_success_indicators or (not has_error and len(cleaned_result.strip()) > 0):
                                                    # Success - create result dict
                                                    confluence_result = {
                                                        'success': True,
                                                        'id': page_id,
                                                        'title': page_title,
                                                        'link': page_url or f"{Config.CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id or 'unknown'}",
                                                        'tool_used': 'MCP Protocol'
                                                    }
                                                    logger.info("Confluence page created successfully via MCP Protocol (parsed from text)")
                                                    if page_id:
                                                        logger.debug(f"Extracted page ID: {page_id}")
                                                    if page_url:
                                                        logger.debug(f"Extracted page URL: {page_url}")
                                                    mcp_data = None  # Skip dict processing, we already have result
                                                    tool_used = "MCP Protocol"  # Ensure tool_used is set
                                                else:
                                                    # Check if it's an error message
                                                    error_msg = cleaned_result[:500] if len(cleaned_result) > 500 else cleaned_result
                                                    raise Exception(f"MCP tool returned non-JSON format (possibly an error): {error_msg}")
                                        elif isinstance(mcp_result, dict):
                                            mcp_data = mcp_result
                                            # Additional check: if dict has success=False but error is boolean
                                            if not mcp_data.get('success') and isinstance(mcp_data.get('error'), bool):
                                                logger.debug(f"WARNING: mcp_data['error'] is boolean {mcp_data.get('error')}, converting to string")
                                                mcp_data['error'] = f"Error flag was set to {mcp_data.get('error')}"
                                        elif mcp_result is True or mcp_result is False:
                                            # Handle boolean result (unexpected)
                                            logger.error(f"MCP tool returned boolean {mcp_result} instead of result dict/string")
                                            raise Exception(f"MCP tool returned boolean {mcp_result} instead of result dict/string. This indicates a bug in the MCP tool wrapper or server.")
                                        else:
                                            logger.debug(f"Unexpected result type: {type(mcp_result)}, value: {repr(mcp_result)[:200]}")
                                            mcp_data = {'success': False, 'error': f'Unexpected result type: {type(mcp_result).__name__}', 'error_detail': str(mcp_result)[:200], 'error_type': type(mcp_result).__name__}
                                        
                                        # Process mcp_data if we have it (skip if we already created confluence_result from text)
                                        if mcp_data is not None and isinstance(mcp_data, dict):
                                            # Rovo MCP Server returns page object directly (no 'success' flag)
                                            # Check for presence of 'id' field (which indicates successful creation)
                                            # Also check for explicit success flag (for custom MCP servers)
                                            has_success_flag = mcp_data.get('success', False)
                                            
                                            # Check for page ID in multiple possible locations
                                            has_page_id = bool(
                                                mcp_data.get('id') or 
                                                mcp_data.get('page_id') or 
                                                mcp_data.get('pageId') or
                                                # Also check nested structures (version object might have id)
                                                (mcp_data.get('version', {}).get('id') if isinstance(mcp_data.get('version'), dict) else False)
                                            )
                                            
                                            # Log what we found for debugging
                                            if has_page_id:
                                                page_id_locations = []
                                                if mcp_data.get('id'):
                                                    page_id_locations.append(f"root.id={mcp_data.get('id')}")
                                                if mcp_data.get('page_id'):
                                                    page_id_locations.append(f"root.page_id={mcp_data.get('page_id')}")
                                                if mcp_data.get('pageId'):
                                                    page_id_locations.append(f"root.pageId={mcp_data.get('pageId')}")
                                                if isinstance(mcp_data.get('version'), dict) and mcp_data.get('version', {}).get('id'):
                                                    page_id_locations.append(f"version.id={mcp_data.get('version', {}).get('id')}")
                                                logger.debug(f"Found page ID indicators: {', '.join(page_id_locations)}")
                                            
                                            if has_success_flag or has_page_id:
                                                # Extract page ID from various possible fields
                                                # Prioritize root-level 'id' field (Rovo format)
                                                page_id = (
                                                    mcp_data.get('id') or 
                                                    mcp_data.get('page_id') or 
                                                    mcp_data.get('pageId') or
                                                    # Extract from _links if available
                                                    (mcp_data.get('_links', {}).get('webui', '').split('pageId=')[-1].split('&')[0] 
                                                     if mcp_data.get('_links', {}).get('webui') else None) or
                                                    # Last resort: check nested version object
                                                    (mcp_data.get('version', {}).get('id') if isinstance(mcp_data.get('version'), dict) else None)
                                                )
                                                
                                                # Convert to string if it's a number
                                                if page_id:
                                                    page_id = str(page_id)
                                                    logger.debug(f"Extracted page ID: {page_id} (type: {type(page_id).__name__})")
                                                
                                                # Extract link from various possible fields
                                                page_link = None
                                                if mcp_data.get('link'):
                                                    page_link = mcp_data.get('link')
                                                elif mcp_data.get('_links', {}).get('webui'):
                                                    webui_path = mcp_data.get('_links', {}).get('webui')
                                                    if webui_path.startswith('http'):
                                                        page_link = webui_path
                                                    else:
                                                        base_url = Config.CONFLUENCE_URL.split('/wiki')[0].rstrip('/')
                                                        page_link = f"{base_url}{webui_path}"
                                                elif page_id:
                                                    page_link = f"{Config.CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id}"
                                                
                                                confluence_result = {
                                                    'success': True,
                                                    'id': page_id,
                                                    'title': mcp_data.get('title', page_title),
                                                    'link': page_link or f"{Config.CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id or 'unknown'}",
                                                    'tool_used': 'MCP Protocol'
                                                }
                                                logger.info(f"Confluence page created successfully via MCP Protocol (ID: {page_id})")
                                            else:
                                                # Extract detailed error information
                                                # Handle case where error might be boolean or other types
                                                error_raw = mcp_data.get('error', 'Unknown MCP error')
                                                error_msg = str(error_raw) if not isinstance(error_raw, bool) else f"Error flag: {error_raw}"
                                                error_detail = str(mcp_data.get('error_detail', ''))
                                                error_type = str(mcp_data.get('error_type', ''))
                                                
                                                # Log full mcp_data for debugging
                                                logger.debug(f"Full mcp_data response: {mcp_data}")
                                                
                                                # Build comprehensive error message
                                                error_parts = []
                                                if error_type and error_type != '':
                                                    error_parts.append(f"Type: {error_type}")
                                                if error_detail and error_detail != '':
                                                    error_parts.append(f"Detail: {error_detail}")
                                                if error_msg and error_msg != 'Unknown MCP error':
                                                    error_parts.append(f"Error: {error_msg}")
                                                
                                                # If no clear error message, include the full response
                                                if not error_parts:
                                                    error_parts.append(f"Full response: {mcp_data}")
                                                
                                                full_error = '; '.join(error_parts) if error_parts else f"Unknown error (mcp_data: {mcp_data})"
                                                raise Exception(f"MCP tool error: {full_error}")
                                    
                                    except concurrent.futures.TimeoutError:
                                        logger.warning("MCP Protocol timeout after 60 seconds, falling back to direct API")
                                        tool_used = None  # Will trigger fallback
                                        # Don't raise exception - allow fallback to direct API
                                        mcp_result = None
                                        use_mcp = False  # Skip MCP processing, go to fallback
                                    
                            except (asyncio.TimeoutError, Exception) as e:
                                # Enhanced error logging
                                error_type = type(e).__name__
                                error_str = str(e) if str(e) else repr(e)
                                
                                logger.warning("MCP Protocol failed")
                                logger.debug(f"Error Type: {error_type}")
                                logger.debug(f"Error Message: {error_str}")
                                
                                # Log traceback for debugging
                                logger.debug("Exception details:", exc_info=True)
                                
                                logger.info("Falling back to direct Confluence API call")
                                tool_used = None  # Will trigger fallback
                                use_mcp = False
            
            # Fallback to direct API if MCP failed or not available
            if not confluence_result and self.confluence_tool:
                if use_mcp:
                    logger.warning("MCP Protocol tool not found or failed, falling back to direct API")
                    if self.mcp_integration and self.mcp_integration._initialized:
                        available_tools = [tool.name for tool in self.mcp_integration.get_tools()]
                        logger.debug(f"Available MCP tools: {available_tools}")
                        if not available_tools:
                            logger.warning("No MCP tools available - MCP integration may not be properly initialized")
                else:
                    logger.debug("MCP not enabled, using direct API")
                logger.info("Creating Confluence page via direct API call...")
                tool_used = "Direct API"
                try:
                    confluence_result = self.confluence_tool.create_page(
                        title=page_title,
                        content=confluence_content
                    )
                    if confluence_result.get('success'):
                        confluence_result['tool_used'] = 'Direct API'
                except Exception as direct_api_error:
                    error_str = str(direct_api_error)
                    # Check if error indicates page already exists (MCP might have succeeded)
                    if 'already exists' in error_str.lower() or 'duplicate' in error_str.lower() or 'same title' in error_str.lower():
                        logger.warning("Direct API error indicates page may already exist (MCP tool may have succeeded)")
                        logger.debug(f"Error: {error_str[:200]}")
                        # Set a failure result but with a helpful message
                        confluence_result = {
                            'success': False,
                            'error': f'Page with title "{page_title}" already exists. The MCP tool may have created it successfully, but we could not verify.',
                            'tool_used': 'Direct API (duplicate error)'
                        }
                    else:
                        # Re-raise other errors
                        raise
            
            # Handle result
            if confluence_result and confluence_result.get('success'):
                state["confluence_result"] = confluence_result
                tool_info = f" (via {tool_used})" if tool_used else ""
                state["messages"].append(AIMessage(
                    content=f"📄 **Confluence Page Created{tool_info}:**\n"
                           f"Title: {confluence_result['title']}\n"
                           f"Link: {confluence_result['link']}"
                ))
                logger.info(f"Confluence page created: {confluence_result['link']}")
            else:
                error_msg = confluence_result.get('error', 'Unknown error') if confluence_result else 'No tool available'
                error_code = confluence_result.get('error_code', 'UNKNOWN') if confluence_result else None
                
                # Create user-friendly error message based on error code
                user_friendly_msg = self._format_confluence_error_message(error_msg, error_code, tool_used)
                
                state["messages"].append(AIMessage(content=user_friendly_msg))
                logger.error(f"Confluence page creation failed: {error_msg} (code: {error_code})")
                
        except Exception as e:
            error_str = str(e)
            error_code = None
            
            # Detect error type from exception
            if 'ConnectionResetError' in error_str or '10054' in error_str or 'connection reset' in error_str.lower():
                error_code = 'CONNECTION_RESET'
            elif 'Connection aborted' in error_str or 'connection aborted' in error_str.lower():
                error_code = 'CONNECTION_ABORTED'
            elif 'timeout' in error_str.lower():
                error_code = 'TIMEOUT'
            elif '401' in error_str or 'unauthorized' in error_str.lower():
                error_code = 'AUTH_ERROR'
            elif '403' in error_str or 'forbidden' in error_str.lower():
                error_code = 'PERMISSION_ERROR'
            
            user_friendly_msg = self._format_confluence_error_message(
                f"An unexpected error occurred: {error_str[:100]}",
                error_code or 'UNKNOWN_ERROR',
                tool_used
            )
            
            state["messages"].append(AIMessage(content=user_friendly_msg))
            logger.error(f"Error creating Confluence page: {e}")
            logger.debug("Exception details:", exc_info=True)
        
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
                        logger.warning("RAG retrieval timeout (15s), proceeding without context")
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
                logger.error(f"Error in RAG retrieval: {e}")
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
            error_str = str(e).lower()
            if 'timeout' in error_str:
                user_message = "I apologize, but the request timed out. Please try again."
            elif 'connection' in error_str or 'network' in error_str:
                user_message = "I apologize, but there was a network connectivity issue. Please check your connection and try again."
            elif 'auth' in error_str or 'unauthorized' in error_str:
                user_message = "I apologize, but there was an authentication issue. Please check your API configuration."
            else:
                user_message = "I apologize, but I encountered an unexpected error. Please try again or rephrase your question."
            
            error_msg = AIMessage(content=user_message)
            messages.append(error_msg)
            state["messages"] = messages
            logger.error(f"Error in RAG query: {e}")
            logger.debug("Exception details:", exc_info=True)
        
        return state
    
    def _handle_coze_agent(self, state: AgentState) -> AgentState:
        """Handle Coze agent execution - route to Coze platform API."""
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        
        logger.info("Coze Agent: Processing request via Coze platform API")
        
        # Check if Coze client is available
        if not self.coze_client or not self.coze_client.is_configured():
            error_msg = (
                "Coze agent is not properly configured. "
                "Please check your COZE_API_TOKEN and COZE_BOT_ID settings."
            )
            state["messages"].append(AIMessage(content=error_msg))
            logger.error("Coze client not available or not configured")
            return state
        
        try:
            # Extract user ID from conversation history if available
            # For now, use a default user ID
            user_id = "default_user"
            
            # Get conversation ID from state if available (for context continuity)
            conversation_id = None
            if state.get("coze_result") and isinstance(state["coze_result"], dict):
                conversation_id = state["coze_result"].get("conversation_id")
            
            # Call Coze API with timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self.coze_client.execute_agent,
                    query=user_input,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                try:
                    # Use configurable timeout, default to 300 seconds
                    coze_timeout = float(Config.COZE_API_TIMEOUT) if hasattr(Config, 'COZE_API_TIMEOUT') else 300.0
                    coze_result = future.result(timeout=coze_timeout)
                except concurrent.futures.TimeoutError:
                    coze_timeout = float(Config.COZE_API_TIMEOUT) if hasattr(Config, 'COZE_API_TIMEOUT') else 300.0
                    timeout_minutes = int(coze_timeout / 60)
                    logger.warning(f"Coze API call timed out ({coze_timeout}s)")
                    error_msg = (
                        f"I apologize, but the Coze agent request timed out after {timeout_minutes} minutes. "
                        "The service may be slow or unavailable. Please try again later."
                    )
                    state["messages"].append(AIMessage(content=error_msg))
                    state["coze_result"] = {
                        "success": False,
                        "error": "Request timeout",
                        "error_type": "timeout"
                    }
                    return state
            
            # Store result in state
            state["coze_result"] = coze_result
            
            if coze_result.get("success"):
                # Extract agent response
                agent_response = coze_result.get("response", "")
                
                if agent_response:
                    # Add agent response to messages
                    state["messages"].append(AIMessage(content=agent_response))
                    logger.info("Coze agent response received successfully")
                else:
                    # Empty response - log raw response for debugging
                    raw_response = coze_result.get("raw_response")
                    logger.warning("Coze agent returned empty response")
                    if raw_response:
                        logger.debug(f"Raw response structure: {raw_response[:500]}...")
                    else:
                        logger.debug("No raw_response in result, checking conversation_id and token_usage")
                        logger.debug(f"Conversation ID: {coze_result.get('conversation_id')}")
                        logger.debug(f"Token usage: {coze_result.get('token_usage')}")
                    
                    error_msg = (
                        "The Coze agent returned an empty response. "
                        "This may indicate the response format is not recognized. "
                        "Please check the logs for details or try again."
                    )
                    state["messages"].append(AIMessage(content=error_msg))
            else:
                # API call failed
                error_message = coze_result.get("error", "Unknown error occurred")
                error_type = coze_result.get("error_type", "unknown")
                
                # Create user-friendly error message
                if error_type == "timeout":
                    user_msg = (
                        "I apologize, but the Coze agent request timed out. "
                        "Please try again later."
                    )
                elif error_type == "http_error" or error_type == "auth_error":
                    status_code = coze_result.get("status_code", 0)
                    coze_error_code = coze_result.get("coze_error_code")
                    
                    # Use the error message from Coze API if available (it's more specific)
                    if error_message and error_message != "Unknown error occurred":
                        # Coze API provides user-friendly messages, use them directly
                        user_msg = (
                            f"I encountered an error with the Coze platform: {error_message}. "
                            f"Please check your COZE_API_TOKEN and COZE_BOT_ID configuration."
                        )
                    elif status_code == 401 or coze_error_code == 4101:
                        user_msg = (
                            "Authentication failed with Coze platform. "
                            "The token you entered is incorrect. Please check your COZE_API_TOKEN "
                            "and ensure it's valid. For more information, refer to "
                            "https://coze.com/docs/developer_guides/authentication"
                        )
                    elif status_code == 403:
                        user_msg = (
                            "Access forbidden. Please check your bot permissions "
                            "and COZE_BOT_ID configuration."
                        )
                    elif status_code == 404 or coze_error_code == 4102:
                        user_msg = (
                            "Bot not found. Please verify your COZE_BOT_ID is correct."
                        )
                    else:
                        user_msg = (
                            f"I encountered an error communicating with the Coze platform "
                            f"(Error: {error_message}). Please try again later."
                        )
                elif error_type == "network_error":
                    user_msg = (
                        "I'm having trouble connecting to the Coze platform. "
                        "Please check your network connection and try again."
                    )
                else:
                    user_msg = (
                        f"I encountered an error: {error_message}. "
                        "Please try again or contact support if the issue persists."
                    )
                
                state["messages"].append(AIMessage(content=user_msg))
                logger.error(f"Coze API call failed: {error_message} (type: {error_type})")
                
        except Exception as e:
            error_str = str(e)
            logger.error(f"Unexpected error in Coze agent handler: {e}")
            logger.debug("Exception details:", exc_info=True)
            
            # Provide user-friendly error message
            if 'timeout' in error_str.lower():
                user_msg = "The Coze agent request timed out. Please try again later."
            elif 'connection' in error_str.lower() or 'network' in error_str.lower():
                user_msg = (
                    "I'm having trouble connecting to the Coze platform. "
                    "Please check your network connection."
                )
            else:
                user_msg = (
                    "I encountered an unexpected error while processing your request. "
                    "Please try again later."
                )
            
            state["messages"].append(AIMessage(content=user_msg))
            state["coze_result"] = {
                "success": False,
                "error": error_str,
                "error_type": "exception"
            }
        
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
    
    def _html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to Markdown format for Rovo MCP Server.
        Basic conversion - handles common HTML tags.
        """
        import re
        
        markdown = html_content
        
        # Convert headings
        markdown = re.sub(r'<h1>(.*?)</h1>', r'# \1', markdown, flags=re.DOTALL)
        markdown = re.sub(r'<h2>(.*?)</h2>', r'## \1', markdown, flags=re.DOTALL)
        markdown = re.sub(r'<h3>(.*?)</h3>', r'### \1', markdown, flags=re.DOTALL)
        markdown = re.sub(r'<h4>(.*?)</h4>', r'#### \1', markdown, flags=re.DOTALL)
        
        # Convert links
        markdown = re.sub(r'<a href="([^"]*)">([^<]*)</a>', r'[\2](\1)', markdown)
        
        # Convert bold
        markdown = re.sub(r'<strong>(.*?)</strong>', r'**\1**', markdown, flags=re.DOTALL)
        markdown = re.sub(r'<b>(.*?)</b>', r'**\1**', markdown, flags=re.DOTALL)
        
        # Convert italic
        markdown = re.sub(r'<em>(.*?)</em>', r'*\1*', markdown, flags=re.DOTALL)
        markdown = re.sub(r'<i>(.*?)</i>', r'*\1*', markdown, flags=re.DOTALL)
        
        # Convert lists
        markdown = re.sub(r'<ul>\s*', '', markdown)
        markdown = re.sub(r'</ul>\s*', '', markdown)
        markdown = re.sub(r'<ol>\s*', '', markdown)
        markdown = re.sub(r'</ol>\s*', '', markdown)
        markdown = re.sub(r'<li>(.*?)</li>', r'- \1\n', markdown, flags=re.DOTALL)
        
        # Convert paragraphs
        markdown = re.sub(r'<p>(.*?)</p>', r'\1\n\n', markdown, flags=re.DOTALL)
        
        # Remove remaining HTML tags
        markdown = re.sub(r'<[^>]+>', '', markdown)
        
        # Clean up whitespace
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        markdown = markdown.strip()
        
        return markdown
    
    def _format_confluence_error_message(self, error_msg: str, error_code: Optional[str] = None, tool_used: Optional[str] = None) -> str:
        """
        Format a user-friendly error message for Confluence page creation failures.
        
        Args:
            error_msg: Raw error message
            error_code: Error code (e.g., 'CONNECTION_RESET', 'AUTH_ERROR')
            tool_used: Which tool was used ('MCP Protocol', 'Direct API', etc.)
            
        Returns:
            User-friendly error message
        """
        tool_info = f" ({tool_used})" if tool_used else ""
        
        # Map error codes to user-friendly messages
        error_messages = {
            'CONNECTION_RESET': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "The connection to Confluence was reset by the server. This usually happens when:\n"
                "- The Confluence server is experiencing high load\n"
                "- There are network connectivity issues\n"
                "- The connection timed out\n\n"
                "**What you can do:**\n"
                "- ✅ Your Jira issue was created successfully\n"
                "- ✅ You can manually create the Confluence page later\n"
                "- ✅ Try again in a few minutes if needed\n"
            ),
            'CONNECTION_ABORTED': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "The connection to Confluence was interrupted. This may be due to:\n"
                "- Network connectivity issues\n"
                "- Firewall or proxy settings blocking the connection\n"
                "- Confluence server temporarily unavailable\n\n"
                "**What you can do:**\n"
                "- ✅ Your Jira issue was created successfully\n"
                "- ✅ Check your network connection\n"
                "- ✅ Try creating the page manually in Confluence\n"
            ),
            'TIMEOUT': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "The request to Confluence timed out. The server may be slow or overloaded.\n\n"
                "**What you can do:**\n"
                "- ✅ Your Jira issue was created successfully\n"
                "- ✅ Try again later when the server is less busy\n"
                "- ✅ Create the Confluence page manually if urgent\n"
            ),
            'AUTH_ERROR': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "Authentication failed. Please check:\n"
                "- ✅ Your Confluence credentials (JIRA_EMAIL and JIRA_API_TOKEN)\n"
                "- ✅ That your API token is valid and not expired\n"
                "- ✅ That your account has access to the Confluence space\n\n"
                "**Note:** Your Jira issue was created successfully."
            ),
            'PERMISSION_ERROR': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "Permission denied. Your account doesn't have permission to create pages in this space.\n\n"
                "**Please check:**\n"
                "- ✅ Your API token has write permissions for Confluence\n"
                "- ✅ Your account has access to the space: {space_key}\n"
                "- ✅ Contact your Confluence administrator if needed\n\n"
                "**Note:** Your Jira issue was created successfully."
            ),
            'SPACE_NOT_FOUND': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "The Confluence space was not found. Please verify:\n"
                "- ✅ CONFLUENCE_SPACE_KEY is set correctly in your .env file\n"
                "- ✅ The space key exists in your Confluence instance\n"
                "- ✅ Your account has access to this space\n\n"
                "**Note:** Your Jira issue was created successfully."
            ),
            'CONNECTION_ERROR': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "Unable to connect to Confluence server. Please check:\n"
                "- ✅ CONFLUENCE_URL is correct in your .env file\n"
                "- ✅ Your network connection is working\n"
                "- ✅ Confluence server is accessible\n\n"
                "**What you can do:**\n"
                "- ✅ Your Jira issue was created successfully\n"
                "- ✅ Try again later or create the page manually\n"
            ),
            'NETWORK_ERROR': (
                "⚠ **Confluence page creation failed{tool_info}:**\n\n"
                "A network error occurred while connecting to Confluence.\n\n"
                "**What you can do:**\n"
                "- ✅ Your Jira issue was created successfully\n"
                "- ✅ Check your network connection\n"
                "- ✅ Try again in a few moments\n"
            )
        }
        
        # Get space key for error message
        space_key = getattr(Config, 'CONFLUENCE_SPACE_KEY', 'the configured space')
        
        # Use specific error message if available, otherwise use generic
        if error_code and error_code in error_messages:
            base_msg = error_messages[error_code]
            return base_msg.format(tool_info=tool_info, space_key=space_key)
        else:
            # Generic error message
            return (
                f"⚠ **Confluence page creation failed{tool_info}:**\n\n"
                f"The system attempted to create the Confluence page but encountered an issue.\n\n"
                f"**What happened:**\n"
                f"- Tried to use MCP protocol first\n"
                f"- Fell back to direct API call\n"
                f"- Both methods encountered issues\n\n"
                f"**Please check:**\n"
                f"- ✅ CONFLUENCE_URL and CONFLUENCE_SPACE_KEY in .env file\n"
                f"- ✅ API token has Confluence write permissions\n"
                f"- ✅ Network connectivity to Confluence\n"
                f"- ✅ Confluence server is accessible\n\n"
                f"**Good news:** Your Jira issue was created successfully! ✅\n"
                f"You can create the Confluence page manually if needed."
            )
    
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
        
        return "I apologize, but I couldn't generate a response."

