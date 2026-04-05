"""Helper functions for Confluence creation node result parsing and messaging."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional


CONFLUENCE_TOOL_NAME_PATTERNS = [
    "createConfluencePage",
    "getConfluencePage",
    "updateConfluencePage",
    "getConfluenceSpaces",
    "getPagesInConfluenceSpace",
    "getConfluencePageAncestors",
    "getConfluencePageDescendants",
    "createConfluenceFooterComment",
    "createConfluenceInlineComment",
    "getConfluencePageFooterComments",
    "getConfluencePageInlineComments",
    "searchConfluenceUsingCql",
    "create_confluence_page",
    "confluence_create_page",
    "create_page",
    "confluence_page_create",
    "confluence_create",
    "create_confluence",
    "atlassian_confluence_create_page",
    "atlassian_create_page",
    "rovo_create_page",
    "rovo_confluence_create",
]


def select_mcp_confluence_tool(mcp_integration: Any) -> Optional[Any]:
    """Return the best available Confluence MCP tool, excluding Jira tools."""
    for tool_name in CONFLUENCE_TOOL_NAME_PATTERNS:
        tool = mcp_integration.get_tool(tool_name)
        if tool and _looks_like_confluence_tool(tool.name):
            return tool

    for tool in mcp_integration.get_tools():
        if _looks_like_confluence_tool(tool.name):
            return tool

    return None


def is_rovo_confluence_tool(tool_name: str) -> bool:
    """Return True when the tool name matches official camelCase Rovo Confluence tools."""
    return any(char.isupper() for char in tool_name or "") and "Confluence" in (tool_name or "")


def extract_confluence_tool_schema(tool: Any) -> Optional[Dict[str, Any]]:
    """Extract a normalized input schema from a tool's private schema or args_schema model."""
    if hasattr(tool, "_tool_schema") and tool._tool_schema:
        return tool._tool_schema

    if hasattr(tool, "args_schema") and tool.args_schema and hasattr(tool.args_schema, "model_fields"):
        properties = {}
        for field_name, field_info in tool.args_schema.model_fields.items():
            properties[field_name] = {
                "type": "string",
                "description": field_info.description if hasattr(field_info, "description") else "",
            }
        return {"inputSchema": {"properties": properties}}

    return None


def build_confluence_mcp_args(
    *,
    tool_name: str,
    tool_schema: Optional[Dict[str, Any]],
    page_title: str,
    confluence_content: str,
    markdown_content: str,
    space_key: str,
    cloud_id: Optional[str],
    resolve_space_id: Callable[[str, Optional[str]], Optional[Any]],
) -> Dict[str, Any]:
    """Build MCP tool arguments from schema metadata while preserving current fallback behavior."""
    if tool_schema and "inputSchema" in tool_schema:
        return _build_schema_driven_mcp_args(
            tool_name=tool_name,
            tool_schema=tool_schema,
            page_title=page_title,
            confluence_content=confluence_content,
            markdown_content=markdown_content,
            space_key=space_key,
            cloud_id=cloud_id,
            resolve_space_id=resolve_space_id,
        )

    return _build_fallback_mcp_args(
        page_title=page_title,
        confluence_content=confluence_content,
        space_key=space_key,
        cloud_id=cloud_id,
    )


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


def _build_schema_driven_mcp_args(
    *,
    tool_name: str,
    tool_schema: Dict[str, Any],
    page_title: str,
    confluence_content: str,
    markdown_content: str,
    space_key: str,
    cloud_id: Optional[str],
    resolve_space_id: Callable[[str, Optional[str]], Optional[Any]],
) -> Dict[str, Any]:
    input_schema = tool_schema["inputSchema"]
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    mcp_args: Dict[str, Any] = {}

    content_format_enum = None
    content_format_param = None
    for param_name, param_def in properties.items():
        param_lower = param_name.lower()
        if "contentformat" in param_lower or param_name == "contentFormat":
            content_format_param = param_name
            if "enum" in param_def:
                content_format_enum = param_def["enum"]
            elif "anyOf" in param_def:
                for any_of_item in param_def["anyOf"]:
                    if "enum" in any_of_item:
                        content_format_enum = any_of_item["enum"]
                        break
            break

    for param_name in properties.keys():
        param_lower = param_name.lower()
        if "cloudid" in param_lower or param_name == "cloudId":
            if cloud_id:
                mcp_args[param_name] = cloud_id
        elif "contentformat" in param_lower or param_name == "contentFormat":
            mcp_args[param_name] = content_format_enum[0] if content_format_enum else "markdown"
        elif any(mapped in param_lower for mapped in ["title", "name", "pagetitle"]):
            mcp_args[param_name] = page_title
        elif any(mapped in param_lower for mapped in ["content", "body", "html", "text", "description"]):
            content_format_value = mcp_args.get(content_format_param or "contentFormat", "")
            mcp_args[param_name] = markdown_content if content_format_value == "markdown" else confluence_content
        elif any(mapped in param_lower for mapped in ["space", "spacekey", "spaceid"]):
            mcp_args[param_name] = _resolve_space_parameter(
                param_name=param_name,
                param_lower=param_lower,
                space_key=space_key,
                cloud_id=cloud_id,
                resolve_space_id=resolve_space_id,
            )

    for req_param in required:
        if req_param in mcp_args:
            continue

        req_lower = req_param.lower()
        if "title" in req_lower or "name" in req_lower:
            mcp_args[req_param] = page_title
        elif "content" in req_lower or "body" in req_lower or "description" in req_lower:
            content_format_value = mcp_args.get(content_format_param or "contentFormat", "")
            mcp_args[req_param] = markdown_content if content_format_value == "markdown" else confluence_content
        elif "space" in req_lower:
            mcp_args[req_param] = _resolve_space_parameter(
                param_name=req_param,
                param_lower=req_lower,
                space_key=space_key,
                cloud_id=cloud_id,
                resolve_space_id=resolve_space_id,
            )
        elif "cloudid" in req_lower or req_param == "cloudId":
            if cloud_id:
                mcp_args[req_param] = cloud_id
        elif "contentformat" in req_lower or req_param == "contentFormat":
            mcp_args[req_param] = "markdown"

    return mcp_args


def _build_fallback_mcp_args(
    *,
    page_title: str,
    confluence_content: str,
    space_key: str,
    cloud_id: Optional[str],
) -> Dict[str, Any]:
    args = {
        "title": page_title,
        "content": confluence_content,
        "space_key": space_key,
        "spaceKey": space_key,
        "space": space_key,
        "spaceId": space_key,
        "body": confluence_content,
        "html": confluence_content,
        "text": confluence_content,
        "summary": page_title,
        "description": confluence_content,
        "contentFormat": "markdown",
    }
    if cloud_id:
        args["cloudId"] = cloud_id
    return args


def _resolve_space_parameter(
    *,
    param_name: str,
    param_lower: str,
    space_key: str,
    cloud_id: Optional[str],
    resolve_space_id: Callable[[str, Optional[str]], Optional[Any]],
) -> str:
    if "spaceid" in param_lower or param_name == "spaceId":
        space_id = resolve_space_id(space_key, cloud_id)
        return str(space_id) if space_id else space_key
    return space_key


def _looks_like_confluence_tool(tool_name: str) -> bool:
    tool_name_lower = (tool_name or "").lower()
    if "jira" in tool_name_lower or "issue" in tool_name_lower:
        return False

    jira_keywords = ["ticket", "bug", "story", "task", "epic", "sprint"]
    if any(keyword in tool_name_lower for keyword in jira_keywords) and "confluence" not in tool_name_lower:
        return False

    is_official_rovo = (
        "Confluence" in (tool_name or "")
        and any(keyword in (tool_name or "") for keyword in ["create", "get", "update", "search", "page", "space", "comment"])
    )
    is_confluence_tool = (
        "confluence" in tool_name_lower
        or ("rovo" in tool_name_lower and ("page" in tool_name_lower or "create" in tool_name_lower))
        or ("page" in tool_name_lower and "create" in tool_name_lower and "jira" not in tool_name_lower)
    )
    return is_official_rovo or is_confluence_tool
