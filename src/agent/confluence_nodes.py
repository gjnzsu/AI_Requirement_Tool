"""Helper functions for Confluence creation node result parsing and messaging."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def build_confluence_page_link(
    confluence_url: str,
    *,
    page_id: Optional[str] = None,
    explicit_link: Optional[str] = None,
    webui_path: Optional[str] = None,
) -> str:
    """Build a normalized Confluence Cloud page link from available result fields."""
    base_url = (confluence_url or "").split("/wiki")[0].rstrip("/")

    if explicit_link:
        if explicit_link.startswith("http"):
            return explicit_link
        return f"{base_url}/wiki{explicit_link}"

    if webui_path:
        if webui_path.startswith("http"):
            return webui_path
        return f"{base_url}/wiki{webui_path}"

    page_id = str(page_id) if page_id else "unknown"
    return f"{base_url}/wiki/pages/viewpage.action?pageId={page_id}"


def normalize_mcp_confluence_text_result(
    text_result: str,
    *,
    page_title: str,
    confluence_url: str,
) -> Dict[str, Any]:
    """Parse a text MCP response into the standard success result shape."""
    cleaned_result = (text_result or "").strip()

    if cleaned_result.startswith("Error:"):
        raise ValueError(f"MCP tool returned error: {cleaned_result[:500]}")

    error_keywords = ["failed", "invalid", "unauthorized", "forbidden", "not found", "404", "500"]
    has_error = any(keyword in cleaned_result.lower() for keyword in error_keywords)

    if has_error and "success" not in cleaned_result.lower() and "created" not in cleaned_result.lower():
        raise ValueError(
            f"MCP tool returned error message: {cleaned_result[:500]}"
        )

    page_id_match = re.search(r"(?:page[_\s]?id|pageId|id)[\s:=]+(\d+)", cleaned_result, re.IGNORECASE)
    page_id = page_id_match.group(1) if page_id_match else None
    url_match = re.search(r"https?://[^\s\)]+", cleaned_result)
    page_url = url_match.group(0) if url_match else None

    has_success_indicators = (
        "created" in cleaned_result.lower()
        or "success" in cleaned_result.lower()
        or page_id
        or page_url
        or "confluence" in cleaned_result.lower()
    )

    if not has_success_indicators and not cleaned_result:
        raise ValueError("MCP tool returned non-JSON format (possibly an error): ")

    return {
        "success": True,
        "id": page_id,
        "title": page_title,
        "link": build_confluence_page_link(
            confluence_url,
            page_id=page_id,
            explicit_link=page_url,
        ),
        "tool_used": "MCP Protocol",
    }


def normalize_mcp_confluence_dict_result(
    mcp_data: Dict[str, Any],
    *,
    page_title: str,
    confluence_url: str,
) -> Dict[str, Any]:
    """Normalize Rovo/custom MCP Confluence payloads into the standard success result shape."""
    has_success_flag = mcp_data.get("success", False)
    page_id = _extract_mcp_page_id(mcp_data)

    if has_success_flag or page_id:
        return {
            "success": True,
            "id": page_id,
            "title": mcp_data.get("title", page_title),
            "link": build_confluence_page_link(
                confluence_url,
                page_id=page_id,
                explicit_link=mcp_data.get("link"),
                webui_path=(mcp_data.get("_links", {}) or {}).get("webui"),
            ),
            "tool_used": "MCP Protocol",
        }

    error_raw = mcp_data.get("error", "Unknown MCP error")
    error_msg = str(error_raw) if not isinstance(error_raw, bool) else f"Error flag: {error_raw}"
    error_detail = str(mcp_data.get("error_detail", ""))
    error_type = str(mcp_data.get("error_type", ""))

    error_parts = []
    if error_type:
        error_parts.append(f"Type: {error_type}")
    if error_detail:
        error_parts.append(f"Detail: {error_detail}")
    if error_msg and error_msg != "Unknown MCP error":
        error_parts.append(f"Error: {error_msg}")
    if not error_parts:
        error_parts.append(f"Full response: {mcp_data}")

    raise ValueError(f"MCP tool error: {'; '.join(error_parts)}")


def build_confluence_duplicate_result(page_title: str) -> Dict[str, Any]:
    """Build the duplicate-page fallback result used after a direct API exception."""
    return {
        "success": False,
        "error": (
            f'Page with title "{page_title}" already exists. '
            "The MCP tool may have created it successfully, but we could not verify."
        ),
        "tool_used": "Direct API (duplicate error)",
    }


def build_confluence_success_message(confluence_result: Dict[str, Any], tool_used: Optional[str]) -> str:
    """Build the user-facing Confluence success message."""
    tool_info = f" (via {tool_used})" if tool_used else ""
    return (
        f"📄 **Confluence Page Created{tool_info}:**\n"
        f"Title: {confluence_result['title']}\n"
        f"Link: {confluence_result['link']}"
    )


def build_confluence_rag_metadata(
    *,
    page_title: str,
    issue_key: str,
    confluence_result: Dict[str, Any],
    created_at: str,
) -> Dict[str, Any]:
    """Build the metadata payload used when ingesting Confluence pages into RAG."""
    return {
        "type": "confluence_page",
        "title": page_title,
        "related_jira": issue_key,
        "link": confluence_result.get("link", ""),
        "page_id": confluence_result.get("id", ""),
        "created_at": created_at,
    }


def detect_confluence_error_code(error_text: str) -> Optional[str]:
    """Map exception/error text to the existing Confluence error-code categories."""
    normalized_error = error_text or ""
    normalized_lower = normalized_error.lower()

    if "ConnectionResetError" in normalized_error or "10054" in normalized_error or "connection reset" in normalized_lower:
        return "CONNECTION_RESET"
    if "Connection aborted" in normalized_error or "connection aborted" in normalized_lower:
        return "CONNECTION_ABORTED"
    if "timeout" in normalized_lower:
        return "TIMEOUT"
    if "401" in normalized_error or "unauthorized" in normalized_lower:
        return "AUTH_ERROR"
    if "403" in normalized_error or "forbidden" in normalized_lower:
        return "PERMISSION_ERROR"
    return None


def build_confluence_error_message(
    *,
    error_code: Optional[str],
    tool_used: Optional[str],
    space_key: str,
) -> str:
    """Build a user-friendly Confluence error message from the existing error-code mapping."""
    tool_info = f" ({tool_used})" if tool_used else ""
    error_messages = {
        "CONNECTION_RESET": (
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
        "CONNECTION_ABORTED": (
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
        "TIMEOUT": (
            "⚠ **Confluence page creation failed{tool_info}:**\n\n"
            "The request to Confluence timed out. The server may be slow or overloaded.\n\n"
            "**What you can do:**\n"
            "- ✅ Your Jira issue was created successfully\n"
            "- ✅ Try again later when the server is less busy\n"
            "- ✅ Create the Confluence page manually if urgent\n"
        ),
        "AUTH_ERROR": (
            "⚠ **Confluence page creation failed{tool_info}:**\n\n"
            "Authentication failed. Please check:\n"
            "- ✅ Your Confluence credentials (JIRA_EMAIL and JIRA_API_TOKEN)\n"
            "- ✅ That your API token is valid and not expired\n"
            "- ✅ That your account has access to the Confluence space\n\n"
            "**Note:** Your Jira issue was created successfully."
        ),
        "PERMISSION_ERROR": (
            "⚠ **Confluence page creation failed{tool_info}:**\n\n"
            "Permission denied. Your account doesn't have permission to create pages in this space.\n\n"
            "**Please check:**\n"
            "- ✅ Your API token has write permissions for Confluence\n"
            "- ✅ Your account has access to the space: {space_key}\n"
            "- ✅ Contact your Confluence administrator if needed\n\n"
            "**Note:** Your Jira issue was created successfully."
        ),
        "SPACE_NOT_FOUND": (
            "⚠ **Confluence page creation failed{tool_info}:**\n\n"
            "The Confluence space was not found. Please verify:\n"
            "- ✅ CONFLUENCE_SPACE_KEY is set correctly in your .env file\n"
            "- ✅ The space key exists in your Confluence instance\n"
            "- ✅ Your account has access to this space\n\n"
            "**Note:** Your Jira issue was created successfully."
        ),
        "CONNECTION_ERROR": (
            "⚠ **Confluence page creation failed{tool_info}:**\n\n"
            "Unable to connect to Confluence server. Please check:\n"
            "- ✅ CONFLUENCE_URL is correct in your .env file\n"
            "- ✅ Your network connection is working\n"
            "- ✅ Confluence server is accessible\n\n"
            "**What you can do:**\n"
            "- ✅ Your Jira issue was created successfully\n"
            "- ✅ Try again later or create the page manually\n"
        ),
        "NETWORK_ERROR": (
            "⚠ **Confluence page creation failed{tool_info}:**\n\n"
            "A network error occurred while connecting to Confluence.\n\n"
            "**What you can do:**\n"
            "- ✅ Your Jira issue was created successfully\n"
            "- ✅ Check your network connection\n"
            "- ✅ Try again in a few moments\n"
        ),
    }

    if error_code and error_code in error_messages:
        return error_messages[error_code].format(tool_info=tool_info, space_key=space_key)

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


def _extract_mcp_page_id(mcp_data: Dict[str, Any]) -> Optional[str]:
    page_id = (
        mcp_data.get("id")
        or mcp_data.get("page_id")
        or mcp_data.get("pageId")
        or (
            mcp_data.get("_links", {}).get("webui", "").split("pageId=")[-1].split("&")[0]
            if (mcp_data.get("_links", {}) or {}).get("webui")
            and "pageId=" in (mcp_data.get("_links", {}) or {}).get("webui", "")
            else None
        )
        or (mcp_data.get("version", {}).get("id") if isinstance(mcp_data.get("version"), dict) else None)
    )
    return str(page_id) if page_id else None
