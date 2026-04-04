"""Helper functions for general-chat node parsing and error-message mapping."""

import re
from typing import Any, Dict, Optional, Tuple


CONFLUENCE_PAGE_PATTERNS = [
    r"confluence page (?:for|about|of) ([A-Z]+-\d+)",
    r"confluence page (?:with )?(?:id|page[_\s]?id)[\s:=]+(\d+)",
    r"confluence page (?:titled|title)[\s:]+(.+?)(?:\?|$)",
]


def parse_confluence_page_reference(
    user_input: str,
    confluence_result: Optional[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str]]:
    """Parse Confluence page references from free text and prior creation state."""
    for pattern in CONFLUENCE_PAGE_PATTERNS:
        match = re.search(pattern, user_input or "", re.IGNORECASE)
        if not match:
            continue

        if "id" in pattern.lower():
            return match.group(1), None
        if "title" in pattern.lower():
            return None, match.group(1).strip()
        if confluence_result and confluence_result.get("success"):
            return confluence_result.get("id"), confluence_result.get("title")
        return None, None

    return None, None


def build_confluence_page_context(page_info: Dict[str, Any]) -> str:
    """Format retrieved Confluence page details for appending to the user prompt."""
    page_context = "\n\nConfluence Page Information (retrieved via MCP Protocol):\n"
    page_context += f"Title: {page_info.get('title', 'N/A')}\n"
    page_context += f"Link: {page_info.get('link', 'N/A')}\n"
    if page_info.get("content"):
        content_preview = str(page_info.get("content", ""))[:500]
        page_context += f"Content Preview: {content_preview}...\n"
    return page_context


def build_general_chat_error_message(
    error: Exception,
    provider_name: Optional[str],
) -> Tuple[str, Optional[int]]:
    """Map an LLM call exception to a user-safe message and detected HTTP status."""
    error_type = type(error).__name__
    error_str = str(error).lower()
    http_status_code = _extract_http_status_code(error, error_str)

    is_connection_error = (
        "Connection" in error_type
        or "connection" in error_str
        or "connect" in error_str
        or "network" in error_str
        or "unreachable" in error_str
        or "timeout" in error_str
    ) and http_status_code is None
    is_auth_error = (
        http_status_code in [401, 403]
        or "Authentication" in error_type
        or "auth" in error_str
        or "api key" in error_str
        or "unauthorized" in error_str
        or ("invalid" in error_str and "key" in error_str)
    )
    is_rate_limit_error = (
        http_status_code == 429
        or "RateLimit" in error_type
        or "rate limit" in error_str
        or "rate_limit" in error_str
        or "quota" in error_str
        or "429" in error_str
    )

    if is_connection_error:
        return (
            "I apologize, but I'm having trouble connecting to the AI service. "
            "This could be due to:\n"
            "- Network connectivity issues\n"
            "- API service temporarily unavailable\n"
            "- Firewall or proxy settings\n\n"
            "Please check your network connection and try again."
        ), http_status_code
    if is_auth_error:
        return (
            "I apologize, but there's an authentication issue. "
            "Please check that your API key is correctly configured and has the necessary permissions."
        ), http_status_code
    if is_rate_limit_error:
        provider_label = provider_name.capitalize() if provider_name else "API"
        return (
            f"鈿狅笍 Rate Limit Exceeded\n\n"
            f"I apologize, but the {provider_label} API rate limit has been exceeded. "
            f"This means you've made too many requests in a short period.\n\n"
            f"**What you can do:**\n"
            f"鈥?Wait a few minutes and try again\n"
            f"鈥?Switch to a different model (OpenAI, DeepSeek) if available\n"
            f"鈥?Check your API quota/usage limits in your {provider_label} account\n\n"
            f"Rate limits are temporary and will reset after a short waiting period."
        ), http_status_code

    return (
        "I apologize, but I encountered an error. "
        "Please check your API key and network connection, or try again later."
    ), http_status_code


def _extract_http_status_code(error: Exception, error_str: str) -> Optional[int]:
    if hasattr(error, "status_code"):
        return error.status_code
    if hasattr(error, "response") and hasattr(error.response, "status_code"):
        return error.response.status_code
    if "429" in error_str or "status code 429" in error_str:
        return 429
    if "401" in error_str or "status code 401" in error_str:
        return 401
    if "403" in error_str or "status code 403" in error_str:
        return 403
    return None
