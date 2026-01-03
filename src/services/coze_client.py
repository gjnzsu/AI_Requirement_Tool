"""
Coze Platform API Client

This module provides a client for interacting with ByteDance Coze platform agent API.
Uses the official cozepy SDK for reliable API integration.
"""

import json
import time
from typing import Dict, Any, Optional
from config.config import Config
from src.utils.logger import get_logger

# Try to import official Coze SDK
try:
    from cozepy import (
        Coze, TokenAuth, Message, ChatEventType
    )
    # Import base URL constants (may have different names in different SDK versions)
    try:
        from cozepy import COZE_CN_BASE_URL, COZE_COM_BASE_URL
        COZE_BASE_URL = COZE_COM_BASE_URL  # Use COM as default
    except ImportError:
        try:
            from cozepy import COZE_CN_BASE_URL, COZE_BASE_URL
        except ImportError:
            # Fallback if constants don't exist
            COZE_CN_BASE_URL = "https://api.coze.cn"
            COZE_BASE_URL = "https://api.coze.com"
    COZEPY_AVAILABLE = True
except ImportError as e:
    COZEPY_AVAILABLE = False
    Coze = None
    TokenAuth = None
    Message = None
    COZE_CN_BASE_URL = "https://api.coze.cn"
    COZE_BASE_URL = "https://api.coze.com"
    ChatEventType = None

logger = get_logger('chatbot.services.coze')

if not COZEPY_AVAILABLE:
    logger.warning("cozepy SDK not available. Install with: pip install cozepy")


class CozeClient:
    """
    Client for interacting with Coze platform agent API.
    """
    
    def __init__(self, api_token: Optional[str] = None, bot_id: Optional[str] = None, 
                 base_url: Optional[str] = None):
        """
        Initialize Coze API client using official cozepy SDK.
        
        Args:
            api_token: Coze API token (defaults to Config.COZE_API_TOKEN)
            bot_id: Coze bot/agent ID (defaults to Config.COZE_BOT_ID)
            base_url: Coze API base URL (defaults to Config.COZE_API_BASE_URL)
        """
        if not COZEPY_AVAILABLE:
            raise ImportError(
                "cozepy SDK is required. Install with: pip install cozepy\n"
                "See: https://github.com/coze-dev/coze-py"
            )
        
        # Use provided values, or fall back to Config if None
        # Empty strings are treated as explicitly unset (not configured)
        self.api_token = api_token if api_token is not None else Config.COZE_API_TOKEN
        self.bot_id = bot_id if bot_id is not None else Config.COZE_BOT_ID
        
        # Determine base URL - use SDK constants if available
        if base_url is not None:
            self.base_url = base_url.rstrip('/')
        elif Config.COZE_API_BASE_URL:
            self.base_url = Config.COZE_API_BASE_URL.rstrip('/')
        else:
            # Default to international API (use SDK constant if available)
            if COZEPY_AVAILABLE and 'COZE_BASE_URL' in globals():
                self.base_url = COZE_BASE_URL
            else:
                self.base_url = "https://api.coze.com"
        
        if not self.api_token:
            logger.warning("Coze API token not configured")
        if not self.bot_id:
            logger.warning("Coze bot ID not configured")
        
        # Initialize Coze SDK client only if token is provided
        # SDK's TokenAuth asserts token length > 0, so we skip initialization if empty
        self.coze_client = None
        if self.api_token:
            try:
                self.coze_client = Coze(
                    auth=TokenAuth(token=self.api_token),
                    base_url=self.base_url
                )
                logger.info(f"Coze SDK client initialized with base_url={self.base_url}")
            except Exception as e:
                logger.error(f"Failed to initialize Coze SDK client: {e}")
                raise
        else:
            logger.debug("Skipping Coze SDK client initialization (no API token provided)")
    
    def is_configured(self) -> bool:
        """Check if Coze client is properly configured."""
        return bool(self.api_token and self.bot_id)
    
    def execute_agent(self, query: str, user_id: str = "default_user", 
                      conversation_id: Optional[str] = None,
                      stream: bool = False) -> Dict[str, Any]:
        """
        Execute Coze agent with a query using official SDK.
        
        Args:
            query: User query/message to send to the agent
            user_id: User identifier (default: "default_user")
            conversation_id: Optional conversation ID for context continuity
            stream: Whether to stream the response (default: False)
            
        Returns:
            Dictionary containing agent response and metadata
            
        Raises:
            ValueError: If client is not properly configured
        """
        if not self.is_configured():
            raise ValueError("Coze client is not properly configured. Please set COZE_API_TOKEN and COZE_BOT_ID.")
        
        if not self.coze_client:
            return {
                "success": False,
                "error": "Coze SDK client not initialized. Please provide a valid COZE_API_TOKEN.",
                "error_type": "configuration_error",
                "status_code": 500
            }
        
        try:
            logger.info(f"Calling Coze API via SDK: bot_id={self.bot_id[:10]}..., user_id={user_id}")
            logger.debug(f"Query: {query[:100]}...")
            
            # Build user message using SDK Message helper
            user_message = Message.build_user_question_text(query)
            
            # Prepare additional messages list
            additional_messages = [user_message]
            
            # Use streaming or non-streaming API based on parameter
            if stream:
                # Streaming API - collect all events
                response_content = ""
                final_conversation_id = conversation_id
                token_usage = None
                
                try:
                    for event in self.coze_client.chat.stream(
                        bot_id=self.bot_id,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        additional_messages=additional_messages
                    ):
                        # Handle different event types
                        if hasattr(event, 'event') and ChatEventType:
                            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                                # Accumulate streaming content
                                if hasattr(event, 'message') and hasattr(event.message, 'content'):
                                    response_content += event.message.content
                            elif event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                                # Chat completed, get final details
                                if hasattr(event, 'chat'):
                                    final_conversation_id = event.chat.conversation_id if hasattr(event.chat, 'conversation_id') else conversation_id
                                    if hasattr(event.chat, 'usage') and hasattr(event.chat.usage, 'token_count'):
                                        token_usage = event.chat.usage.token_count
                        else:
                            # Fallback: try to extract content directly
                            if hasattr(event, 'message') and hasattr(event.message, 'content'):
                                response_content += event.message.content
                    
                    logger.info("Coze API streaming call successful")
                    return {
                        "success": True,
                        "response": response_content,
                        "conversation_id": final_conversation_id or conversation_id,
                        "token_usage": token_usage
                    }
                except Exception as stream_error:
                    logger.error(f"Error in streaming API call: {stream_error}")
                    # Fall through to try non-streaming
                    if response_content:
                        # Return partial response if we got something
                        return {
                            "success": True,
                            "response": response_content,
                            "conversation_id": final_conversation_id or conversation_id,
                            "partial": True
                        }
                    raise
            
            # Use streaming API to get messages as they arrive
            # The create() method returns immediately with IN_PROGRESS status,
            # so we use stream() to get the actual response content
            response_content = ""
            final_conversation_id = conversation_id
            token_usage = None
            
            logger.debug("Using streaming API to retrieve response")
            
            try:
                for event in self.coze_client.chat.stream(
                    bot_id=self.bot_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    additional_messages=additional_messages
                ):
                    # Handle different event types
                    if hasattr(event, 'event') and ChatEventType:
                        event_type = event.event
                        logger.debug(f"Received event: {event_type}")
                        
                        if event_type == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                            # Accumulate streaming content
                            if hasattr(event, 'message') and hasattr(event.message, 'content'):
                                content = event.message.content
                                if isinstance(content, str):
                                    response_content += content
                                elif isinstance(content, list):
                                    for item in content:
                                        if isinstance(item, str):
                                            response_content += item
                                        elif hasattr(item, 'text'):
                                            response_content += item.text
                                        elif isinstance(item, dict) and 'text' in item:
                                            response_content += item['text']
                        
                        elif event_type == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                            # Chat completed, get final details
                            logger.debug("Chat completed")
                            if hasattr(event, 'chat'):
                                chat_obj = event.chat
                                if hasattr(chat_obj, 'conversation_id'):
                                    final_conversation_id = chat_obj.conversation_id
                                if hasattr(chat_obj, 'usage') and hasattr(chat_obj.usage, 'token_count'):
                                    token_usage = chat_obj.usage.token_count
                            # Break out of loop once chat is completed
                            break
                        
                        elif event_type == ChatEventType.CONVERSATION_MESSAGE_COMPLETED:
                            # Message completed, extract final content
                            if hasattr(event, 'message'):
                                msg = event.message
                                if hasattr(msg, 'content'):
                                    content = msg.content
                                    if isinstance(content, str):
                                        if not response_content:  # Use completed message if we don't have delta content
                                            response_content = content
                                    elif isinstance(content, list):
                                        for item in content:
                                            if isinstance(item, str):
                                                if not response_content:
                                                    response_content = item
                                                else:
                                                    response_content += item
                                            elif hasattr(item, 'text'):
                                                response_content += item.text
                                            elif isinstance(item, dict) and 'text' in item:
                                                response_content += item['text']
                    else:
                        # Fallback: try to extract content directly from event
                        if hasattr(event, 'message'):
                            msg = event.message
                            if hasattr(msg, 'content'):
                                content = msg.content
                                if isinstance(content, str):
                                    response_content += content
                                elif isinstance(content, list):
                                    for item in content:
                                        if isinstance(item, str):
                                            response_content += item
                                        elif hasattr(item, 'text'):
                                            response_content += item.text
                
                logger.debug(f"Streaming completed. Response length: {len(response_content)}")
                
            except Exception as stream_error:
                logger.error(f"Error in streaming API: {stream_error}")
                logger.debug("Exception details:", exc_info=True)
                # If streaming fails, fall back to create() and try to extract from conversation
                logger.debug("Falling back to create() method")
                try:
                    chat_response = self.coze_client.chat.create(
                        bot_id=self.bot_id,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        additional_messages=additional_messages
                    )
                    
                    # Wait a bit for chat to complete if still in progress
                    if hasattr(chat_response, 'status'):
                        from cozepy import ChatStatus
                        if chat_response.status == ChatStatus.IN_PROGRESS:
                            logger.debug("Chat still in progress, waiting...")
                            import time
                            time.sleep(2)  # Wait 2 seconds
                            
                            # Try to retrieve conversation messages
                            if hasattr(chat_response, 'conversation_id'):
                                final_conversation_id = chat_response.conversation_id
                                # Retrieve conversation to get messages
                                try:
                                    conv = self.coze_client.conversations.retrieve(conversation_id=final_conversation_id)
                                    if hasattr(conv, 'messages') and conv.messages:
                                        for msg in reversed(conv.messages):
                                            if hasattr(msg, 'role') and msg.role == 'assistant':
                                                if hasattr(msg, 'content'):
                                                    if isinstance(msg.content, str):
                                                        response_content = msg.content
                                                    elif isinstance(msg.content, list):
                                                        for item in msg.content:
                                                            if isinstance(item, str):
                                                                response_content += item
                                                            elif isinstance(item, dict) and 'text' in item:
                                                                response_content += item['text']
                                                break
                                except Exception as e:
                                    logger.debug(f"Could not retrieve conversation: {e}")
                    
                    # Extract from chat_response if still empty
                    if not response_content and hasattr(chat_response, 'messages') and chat_response.messages:
                        for msg in reversed(chat_response.messages):
                            if hasattr(msg, 'role') and msg.role == 'assistant':
                                if hasattr(msg, 'content'):
                                    if isinstance(msg.content, str):
                                        response_content = msg.content
                                    elif isinstance(msg.content, list):
                                        for item in msg.content:
                                            if isinstance(item, str):
                                                response_content += item
                                break
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")
                    raise stream_error  # Re-raise original streaming error
            
            logger.info("Coze API call successful")
            logger.debug(f"Response length: {len(response_content)}")
            if response_content:
                logger.debug(f"Response preview: {response_content[:200]}...")
            else:
                logger.warning("Response content is empty after extraction")
            
            return {
                "success": True,
                "response": response_content,
                "conversation_id": final_conversation_id or conversation_id,
                "token_usage": token_usage,
                "raw_response": str(chat_response) if not response_content else None  # Include raw for debugging
            }
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Coze API call failed: {error_str}")
            logger.debug("Exception details:", exc_info=True)
            
            # Parse error message to extract Coze-specific error codes
            error_msg = error_str
            error_type = "unknown_error"
            status_code = None
            coze_error_code = None
            
            # Check exception type first (more reliable than string matching)
            import concurrent.futures
            if isinstance(e, (TimeoutError, concurrent.futures.TimeoutError)):
                error_type = "timeout"
                error_msg = "Request timed out. The Coze API may be slow or unavailable."
            # Check for common error patterns
            elif "401" in error_str or "unauthorized" in error_str.lower() or "authentication" in error_str.lower():
                error_type = "auth_error"
                status_code = 401
                error_msg = "Authentication failed. Please check your COZE_API_TOKEN."
            elif "404" in error_str or "not found" in error_str.lower():
                error_type = "not_found_error"
                status_code = 404
                error_msg = "Bot not found. Please check your COZE_BOT_ID."
            elif "403" in error_str or "forbidden" in error_str.lower():
                error_type = "http_error"
                status_code = 403
                error_msg = "Access forbidden. Please check your bot permissions."
            elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                error_type = "timeout"
                error_msg = "Request timed out. The Coze API may be slow or unavailable."
            
            # Try to extract Coze error code from exception
            if hasattr(e, 'response'):
                try:
                    if hasattr(e.response, 'json'):
                        error_data = e.response.json()
                        if isinstance(error_data, dict):
                            if "code" in error_data:
                                coze_error_code = error_data.get("code")
                                error_msg = error_data.get("msg", error_msg)
                except:
                    pass
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": error_type,
                "status_code": status_code,
                "coze_error_code": coze_error_code
            }
    

