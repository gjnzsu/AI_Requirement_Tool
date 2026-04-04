"""Helper functions for Coze agent node state/result handling."""

from typing import Any, Dict, Optional, Tuple


def extract_previous_coze_conversation_id(coze_result: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return the prior Coze conversation id when the previous result is a dict."""
    if not isinstance(coze_result, dict):
        return None
    return coze_result.get("conversation_id")


def build_coze_timeout_result(timeout_seconds: float) -> Tuple[str, Dict[str, Any]]:
    """Create timeout user message and structured failure payload."""
    timeout_minutes = int(timeout_seconds / 60)
    user_message = (
        f"I apologize, but the Coze agent request timed out after {timeout_minutes} minutes. "
        "The service may be slow or unavailable. Please try again later."
    )
    return user_message, {
        "success": False,
        "error": "Request timeout",
        "error_type": "timeout",
    }


def resolve_coze_success_message(coze_result: Dict[str, Any]) -> str:
    """Return Coze's agent response, or a user-safe warning when response text is empty."""
    agent_response = coze_result.get("response", "")
    if agent_response:
        return agent_response

    return (
        "The Coze agent returned an empty response. "
        "This may indicate the response format is not recognized. "
        "Please check the logs for details or try again."
    )


def build_coze_failure_message(coze_result: Dict[str, Any]) -> str:
    """Map a Coze error payload to a user-safe response message."""
    error_message = coze_result.get("error", "Unknown error occurred")
    error_type = coze_result.get("error_type", "unknown")

    if error_type == "timeout":
        return "I apologize, but the Coze agent request timed out. Please try again later."

    if error_type in {"http_error", "auth_error"}:
        status_code = coze_result.get("status_code", 0)
        coze_error_code = coze_result.get("coze_error_code")

        if error_message and error_message != "Unknown error occurred":
            return (
                f"I encountered an error with the Coze platform: {error_message}. "
                f"Please check your COZE_API_TOKEN and COZE_BOT_ID configuration."
            )
        if status_code == 401 or coze_error_code == 4101:
            return (
                "Authentication failed with Coze platform. "
                "The token you entered is incorrect. Please check your COZE_API_TOKEN "
                "and ensure it's valid. For more information, refer to "
                "https://coze.com/docs/developer_guides/authentication"
            )
        if status_code == 403:
            return (
                "Access forbidden. Please check your bot permissions "
                "and COZE_BOT_ID configuration."
            )
        if status_code == 404 or coze_error_code == 4102:
            return "Bot not found. Please verify your COZE_BOT_ID is correct."
        return (
            f"I encountered an error communicating with the Coze platform "
            f"(Error: {error_message}). Please try again later."
        )

    if error_type == "network_error":
        return (
            "I'm having trouble connecting to the Coze platform. "
            "Please check your network connection and try again."
        )

    return (
        f"I encountered an error: {error_message}. "
        "Please try again or contact support if the issue persists."
    )


def build_coze_exception_message(error_text: str) -> str:
    """Create a user-safe response for unexpected exceptions in the Coze node."""
    error_text_lower = error_text.lower()
    if "timeout" in error_text_lower:
        return "The Coze agent request timed out. Please try again later."
    if "connection" in error_text_lower or "network" in error_text_lower:
        return (
            "I'm having trouble connecting to the Coze platform. "
            "Please check your network connection."
        )
    return (
        "I encountered an unexpected error while processing your request. "
        "Please try again later."
    )
