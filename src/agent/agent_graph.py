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
from src.agent.callbacks import LLMMonitoringCallback
from src.agent.requirement_workflow import (
    build_backlog_generation_prompt,
    build_requirement_context,
    format_confluence_content,
)
from src.agent.coze_nodes import (
    build_coze_exception_message,
    build_coze_failure_message,
    build_coze_timeout_result,
    extract_previous_coze_conversation_id,
    resolve_coze_success_message,
)
from src.agent.confluence_nodes import (
    build_confluence_exception_outcome,
    build_confluence_failure_outcome,
    build_confluence_success_outcome,
    create_confluence_page_via_direct_api,
    initialize_confluence_mcp_integration,
    is_confluence_tool_name,
    invoke_mcp_confluence_tool,
    select_mcp_confluence_tool,
)
from src.agent.general_chat_nodes import (
    build_confluence_page_context,
    build_general_chat_error_message,
    parse_confluence_page_reference,
)
from src.agent.intent_routing import detect_keyword_intent
from src.agent.jira_nodes import (
    build_jira_exception_outcome,
    build_jira_failure_outcome,
    build_jira_success_outcome,
    create_jira_issue_via_custom_tool,
    initialize_jira_mcp_integration,
    invoke_mcp_jira_tool,
    select_mcp_jira_tool,
)
from src.agent.rag_nodes import (
    build_rag_error_message,
    build_rag_prompt,
    extract_chunk_contents,
    extract_jira_key,
    load_direct_jira_context,
)
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
    
    def _ingest_to_rag(self, content: str, metadata: dict) -> Optional[str]:
        """
        Ingest content into RAG knowledge base for future retrieval.
        
        This method is called after successful Jira/Confluence creation to
        automatically capture organizational knowledge.
        
        Args:
            content: Text content to ingest
            metadata: Metadata dict (type, key, title, link, etc.)
            
        Returns:
            Document ID if successful, None otherwise
        """
        import concurrent.futures
        import time
        
        if not self._rag_service:
            logger.debug("RAG service not available, skipping ingestion")
            return None
        
        doc_type = metadata.get('type', 'unknown')
        doc_key = metadata.get('key', metadata.get('title', ''))
        
        try:
            # Generate unique document ID based on type and key/title for deduplication
            custom_doc_id = f"{doc_type}:{doc_key}" if doc_key else None
            
            # Use timeout to prevent RAG ingestion from blocking the response
            RAG_INGEST_TIMEOUT = 10  # 10 seconds max for RAG ingestion
            
            def do_ingest():
                return self._rag_service.ingest_text(content, metadata, document_id=custom_doc_id)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(do_ingest)
                try:
                    doc_id = future.result(timeout=RAG_INGEST_TIMEOUT)
                    logger.info(f"Ingested to RAG: {doc_type} - {doc_key}")
                    return doc_id
                except concurrent.futures.TimeoutError:
                    logger.warning(f"RAG ingestion timeout for {doc_type}: {doc_key}")
                    return None
                    
        except Exception as e:
            # Non-blocking: log but don't raise
            logger.warning(f"Failed to ingest to RAG: {e}")
            return None
    
    def _detect_intent(self, state: AgentState) -> AgentState:
        """Detect user intent from the input with comprehensive keyword-based detection."""
        user_input = state.get("user_input", "").lower()
        messages = state.get("messages", [])
        logger.debug(f"Detecting intent for input: '{user_input[:50]}...'")

        keyword_intent = detect_keyword_intent(
            state.get("user_input", ""),
            rag_service_available=getattr(self, '_rag_service', None) is not None,
            jira_available=bool(self.jira_tool or (self.use_mcp and self.mcp_integration)),
            coze_enabled=Config.COZE_ENABLED,
        )
        if keyword_intent:
            state["intent"] = keyword_intent
            logger.debug(f"Intent: {keyword_intent} (keyword routing)")
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
        page_id, page_title = parse_confluence_page_reference(
            user_input,
            state.get("confluence_result"),
        )
        
        # If we found a page reference, try to retrieve it using MCP
        if page_id or page_title:
            logger.debug("Detected Confluence page query, attempting MCP retrieval...")
            page_info = self._retrieve_confluence_page_info(page_id=page_id, page_title=page_title)
            
            if page_info.get('success'):
                user_input = user_input + build_confluence_page_context(page_info)
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
                    user_message, http_status_code = build_general_chat_error_message(
                        executor_error,
                        self.provider_name,
                    )

                    if (
                        http_status_code is None
                        and (
                            'Connection' in error_type
                            or 'connection' in error_str
                            or 'connect' in error_str
                            or 'network' in error_str
                            or 'unreachable' in error_str
                            or 'timeout' in error_str
                        )
                    ):
                        logger.debug("Connection error detected, providing user-friendly message")
                    elif http_status_code in [401, 403]:
                        logger.debug("Authentication error detected")
                    elif http_status_code == 429:
                        logger.warning(f"Rate limit error detected (HTTP {http_status_code or 'N/A'}): {executor_error}")
                        logger.debug("Rate limit error detected")
                    else:
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
            if initialize_jira_mcp_integration(self.mcp_integration, timeout_seconds=30.0):
                logger.info("MCP integration initialized successfully")
            else:
                logger.info("Falling back to custom tools")
                use_mcp = False
        
        # Check if we have MCP tools available
        # IMPORTANT: Only use Jira-specific tools, never Confluence tools for Jira operations
        mcp_jira_tool = None
        if use_mcp:
            mcp_jira_tool = select_mcp_jira_tool(self.mcp_integration)
            if not mcp_jira_tool:
                logger.warning("MCP tool 'create_jira_issue' not available, using custom tool")
                use_mcp = False
            else:
                logger.info(f"Found Jira MCP tool: {mcp_jira_tool.name}")
        
        if not use_mcp and not self.jira_tool:
            error_msg = "Jira tool is not configured. Please check your Jira credentials."
            state["messages"].append(AIMessage(content=error_msg))
            return state
        
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        conversation_history = state.get("conversation_history", [])
        
        context_str = build_requirement_context(
            messages=messages[-6:],
            conversation_history=conversation_history[-5:],
        )
        generation_prompt = build_backlog_generation_prompt(
            context_text=context_str,
            user_input=user_input,
        )
        
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
                    result = invoke_mcp_jira_tool(
                        mcp_jira_tool,
                        backlog_data=backlog_data,
                        jira_url=Config.JIRA_URL,
                        timeout_seconds=75.0,
                    )
                    if result is None:
                        logger.info("Falling back to custom tool")
                        tool_used = "Custom Tool (MCP timeout fallback)"
                        result = create_jira_issue_via_custom_tool(
                            self.jira_tool,
                            backlog_data=backlog_data,
                        )
                        if result.get('success'):
                            logger.info(f"Created issue {result.get('key', 'N/A')} via custom tool (MCP timeout)")
                        else:
                            result = {'success': False, 'error': 'MCP tool timed out and custom tool also failed'}
                    else:
                        logger.info(f"Created issue {result['key']} via MCP tool")
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
                            result = create_jira_issue_via_custom_tool(
                                self.jira_tool,
                                backlog_data=backlog_data,
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
                result = create_jira_issue_via_custom_tool(
                    self.jira_tool,
                    backlog_data=backlog_data,
                )
                if result.get('success'):
                    logger.info(f"Custom Tool SUCCESS: Created issue {result.get('key', 'N/A')}")
                else:
                    logger.error(f"Custom Tool FAILED: {result.get('error', 'Unknown error')}")
            
            # Ensure result is set
            if result is None:
                result = {'success': False, 'error': 'No result from Jira creation attempt'}
            
            if result and result.get('success'):
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
        
        jira_result = state.get("jira_result")
        
        # Skip evaluation if no result, not successful, or no evaluator
        if not jira_result or not jira_result.get("success") or not self.jira_evaluator:
            skip_reason = []
            logger.debug(f"Skipping evaluation: no jira_result or evaluator")
            return state
        
        issue_key = jira_result["key"]
        logger.info(f"Starting evaluation for {issue_key}...")
        eval_start = time.time()
        
        try:
            def do_evaluation():
                # Fetch the issue from Jira
                issue = self.jira_evaluator.jira.issue(issue_key)
                issue_dict = {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'description': issue.fields.description or '',
                    'status': issue.fields.status.name,
                    'priority': issue.fields.priority.name if issue.fields.priority else 'Unassigned'
                }
                return self.jira_evaluator.evaluate_maturity(issue_dict)
            
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
                    if initialize_confluence_mcp_integration(self.mcp_integration, timeout_seconds=15.0):
                        logger.info("MCP integration initialized for Confluence")
                    else:
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
                    mcp_confluence_tool = select_mcp_confluence_tool(self.mcp_integration)

                    if mcp_confluence_tool:
                        logger.info(f"Selected MCP Confluence tool: {mcp_confluence_tool.name}")
                    else:
                        logger.warning("No Confluence MCP tools found")
                        logger.debug(f"Available tools: {[tool.name for tool in all_tools]}")
                        logger.debug("This may indicate the Confluence MCP server timed out or isn't configured")
                    
                    if mcp_confluence_tool:
                        # VALIDATION: Final safety check to ensure this is actually a Confluence tool
                        if not is_confluence_tool_name(mcp_confluence_tool.name):
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
                                confluence_result = invoke_mcp_confluence_tool(
                                    mcp_confluence_tool,
                                    page_title=page_title,
                                    confluence_content=confluence_content,
                                    confluence_url=Config.CONFLUENCE_URL,
                                    space_key=Config.CONFLUENCE_SPACE_KEY,
                                    get_cloud_id=self._get_cloud_id,
                                    resolve_space_id=self._get_space_id,
                                    html_to_markdown=self._html_to_markdown,
                                    timeout_seconds=60.0,
                                )

                                if confluence_result is None:
                                    tool_used = None
                                    use_mcp = False
                                else:
                                    logger.info(
                                        "Confluence page created successfully via MCP Protocol (ID: %s)",
                                        confluence_result.get('id'),
                                    )
                                    if confluence_result.get('link'):
                                        logger.debug(f"Extracted page URL: {confluence_result.get('link')}")
                            except Exception as e:
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
                confluence_result = create_confluence_page_via_direct_api(
                    self.confluence_tool,
                    page_title=page_title,
                    confluence_content=confluence_content,
                )
            
            # Handle result
            if confluence_result and confluence_result.get('success'):
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
        user_input = state.get("user_input", "")
        messages = state.get("messages", [])
        
        # Try to get RAG service from state or initialize
        rag_service = getattr(self, '_rag_service', None)
        
        if rag_service:
            try:
                context_str = None
                
                # First, check if user is asking about a specific Jira issue by key
                # Direct document lookup is more reliable than semantic search for specific tickets
                jira_key = extract_jira_key(user_input)
                if jira_key:
                    logger.info(f"RAG: Detected Jira key '{jira_key}', attempting direct document lookup...")
                    context_str = load_direct_jira_context(rag_service.vector_store, jira_key)
                    if context_str:
                        logger.info("RAG: Using direct lookup context for issue-linked documents")
                    else:
                        logger.info(f"RAG: No direct documents found for {jira_key}, falling back to semantic search")
                
                # If no direct lookup results, fall back to semantic search
                if not context_str:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(rag_service.get_context, user_input, 3)
                        try:
                            context_str = future.result(timeout=15.0)  # 15 second timeout for RAG retrieval
                        except concurrent.futures.TimeoutError:
                            logger.warning("RAG retrieval timeout (15s), proceeding without context")
                            context_str = None
                
                if context_str and context_str.strip():
                    rag_prompt = build_rag_prompt(context_str, user_input)
                    # Store raw chunks for reference
                    chunks = rag_service.retrieve(user_input, top_k=3)
                    state["rag_context"] = extract_chunk_contents(chunks)
                    messages.append(HumanMessage(content=rag_prompt))
                else:
                    # No relevant context found, proceed with normal chat
                    logger.info("RAG: No relevant context found, proceeding with normal chat")
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
            user_message = build_rag_error_message(str(e))
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
            conversation_id = extract_previous_coze_conversation_id(state.get("coze_result"))
            
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
                    logger.warning(f"Coze API call timed out ({coze_timeout}s)")
                    timeout_message, timeout_result = build_coze_timeout_result(coze_timeout)
                    state["messages"].append(AIMessage(content=timeout_message))
                    state["coze_result"] = timeout_result
                    return state
            
            # Store result in state
            state["coze_result"] = coze_result
            
            if coze_result.get("success"):
                agent_response = resolve_coze_success_message(coze_result)
                
                if coze_result.get("response", ""):
                    state["messages"].append(AIMessage(content=agent_response))
                    logger.info("Coze agent response received successfully")
                else:
                    raw_response = coze_result.get("raw_response")
                    logger.warning("Coze agent returned empty response")
                    if raw_response:
                        logger.debug(f"Raw response structure: {raw_response[:500]}...")
                    else:
                        logger.debug("No raw_response in result, checking conversation_id and token_usage")
                        logger.debug(f"Conversation ID: {coze_result.get('conversation_id')}")
                        logger.debug(f"Token usage: {coze_result.get('token_usage')}")

                    state["messages"].append(AIMessage(content=agent_response))
            else:
                error_message = coze_result.get("error", "Unknown error occurred")
                error_type = coze_result.get("error_type", "unknown")
                user_msg = build_coze_failure_message(coze_result)
                state["messages"].append(AIMessage(content=user_msg))
                logger.error(f"Coze API call failed: {error_message} (type: {error_type})")
                
        except Exception as e:
            error_str = str(e)
            logger.error(f"Unexpected error in Coze agent handler: {e}")
            logger.debug("Exception details:", exc_info=True)
            
            user_msg = build_coze_exception_message(error_str)
            state["messages"].append(AIMessage(content=user_msg))
            state["coze_result"] = {
                "success": False,
                "error": error_str,
                "error_type": "exception"
            }
        
        return state
    
    def _format_messages_for_context(self, messages: List[BaseMessage]) -> str:
        """Format messages for context string."""
        return build_requirement_context(messages=messages, conversation_history=[])
    
    def _format_confluence_content(self, issue_key: str, backlog_data: Dict, 
                                   evaluation: Dict, jira_link: str) -> str:
        """Format content for Confluence page in HTML format."""
        return format_confluence_content(
            issue_key=issue_key,
            backlog_data=backlog_data,
            evaluation=evaluation,
            jira_link=jira_link,
        )
    
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
    
    def _simplify_for_rag(self, issue_key: str, backlog_data: Dict, 
                          evaluation: Dict, confluence_link: str) -> str:
        """
        Create a simplified, compact text version for RAG ingestion.
        
        This reduces content size significantly to minimize embedding API calls
        while preserving searchable keywords and key information.
        
        Args:
            issue_key: Jira issue key
            backlog_data: Backlog data dict
            evaluation: Evaluation results dict
            confluence_link: Link to Confluence page
            
        Returns:
            Simplified plain text (target: <1000 chars for 1-2 chunks)
        """
        parts = []
        
        # Essential identifiers
        summary = backlog_data.get('summary', 'Untitled')
        parts.append(f"Confluence: {issue_key} - {summary}")
        parts.append(f"Link: {confluence_link}")
        
        # Priority (short)
        priority = backlog_data.get('priority', 'Medium')
        parts.append(f"Priority: {priority}")
        
        # Business value (truncate if long)
        business_value = backlog_data.get('business_value', '')
        if business_value:
            # Keep first 150 chars
            bv_short = business_value[:150] + "..." if len(business_value) > 150 else business_value
            parts.append(f"Business Value: {bv_short}")
        
        # Acceptance criteria (just count and first item)
        acceptance_criteria = backlog_data.get('acceptance_criteria', [])
        if acceptance_criteria:
            parts.append(f"Acceptance Criteria: {len(acceptance_criteria)} items")
            if acceptance_criteria[0]:
                ac_first = acceptance_criteria[0][:80] + "..." if len(acceptance_criteria[0]) > 80 else acceptance_criteria[0]
                parts.append(f"  - {ac_first}")
        
        # Evaluation summary (just score, no details)
        if evaluation and 'overall_maturity_score' in evaluation:
            score = evaluation['overall_maturity_score']
            parts.append(f"Maturity Score: {score}/100")
            
            # Just list criteria names with scores (compact)
            detailed = evaluation.get('detailed_scores', {})
            if detailed:
                score_summary = ", ".join([f"{k.replace('_', ' ')}: {v}" for k, v in detailed.items()])
                # Truncate if too long
                if len(score_summary) > 200:
                    score_summary = score_summary[:200] + "..."
                parts.append(f"Scores: {score_summary}")
        
        # Keywords for search
        parts.append(f"Keywords: confluence page, {issue_key}, requirements, documentation")
        
        return "\n".join(parts)
    
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


