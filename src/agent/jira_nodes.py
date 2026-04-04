"""Helper functions for Jira creation node tool selection and result formatting."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional


PREFERRED_JIRA_MCP_TOOL_NAMES = ["create_jira_issue", "createJiraIssue", "createIssue"]


def select_mcp_jira_tool(mcp_integration: Any) -> Optional[Any]:
    """Return the best Jira MCP tool, excluding Confluence/page tools."""
    for tool_name in PREFERRED_JIRA_MCP_TOOL_NAMES:
        tool = mcp_integration.get_tool(tool_name)
        if tool and _is_jira_creation_tool(tool.name):
            return tool

    for tool in mcp_integration.get_tools():
        if _is_jira_creation_tool(tool.name):
            return tool

    return None


def normalize_mcp_jira_result(mcp_result: Any, *, jira_url: str) -> Dict[str, Any]:
    """Parse MCP Jira tool output and return the normalized custom-tool style payload."""
    mcp_data = _parse_mcp_result_payload(mcp_result)
    if not mcp_data.get("success"):
        error_message = mcp_data.get("error", "Unknown error")
        raise ValueError(f"MCP tool error: {error_message}")

    issue_key = mcp_data.get("ticket_id") or mcp_data.get("issue_key") or ""
    return {
        "success": True,
        "key": issue_key,
        "link": mcp_data.get("link", f"{jira_url}/browse/{issue_key}"),
        "created_by": mcp_data.get("created_by", "MCP_SERVER"),
        "tool_used": mcp_data.get("tool_used", "custom-jira-mcp-server"),
    }


def build_jira_creation_success_message(
    issue_key: str,
    issue_link: str,
    tool_used: str,
) -> str:
    """Build the success message appended to the graph state."""
    return (
        f"✅ Successfully created Jira issue: **{issue_key}**\n"
        f"Link: {issue_link}\n\n"
        f"_(Created using {tool_used})_"
    )


def build_jira_creation_error_message(error_text: str, *, from_exception: bool = False) -> str:
    """Build user-safe Jira creation error messages while preserving timeout handling."""
    normalized_error = (error_text or "").lower()
    if "timeout" in normalized_error or "timed out" in normalized_error:
        if from_exception:
            return (
                "⚠ **Jira issue creation failed:**\n\n"
                "The request timed out. This may happen when:\n"
                "- The Jira server is slow or overloaded\n"
                "- There are network connectivity issues\n\n"
                "**What you can do:**\n"
                "- ✅ Try again in a few moments\n"
                "- ✅ Check your network connection\n"
                "- ✅ Create the issue manually in Jira if urgent\n"
            )

        return (
            "❌ **Jira Creation Timeout**\n\n"
            "The request to create a Jira issue timed out. This could be due to:\n"
            "- Network connectivity issues\n"
            "- Jira server being slow or temporarily unavailable\n"
            "- MCP server taking too long to respond\n\n"
            "**What happened:**\n"
            "- Attempted to use MCP protocol first\n"
            "- Request timed out after 60+ seconds\n"
            "- Attempted fallback to direct API\n\n"
            "**Please try:**\n"
            "- Check your network connection\n"
            "- Verify Jira server is accessible\n"
            "- Try again in a few moments"
        )

    if from_exception:
        return (
            "⚠ **Jira issue creation failed:**\n\n"
            "An unexpected error occurred while creating the Jira issue.\n\n"
            "**What you can do:**\n"
            "- ✅ Try again in a few moments\n"
            "- ✅ Check your Jira configuration (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)\n"
            "- ✅ Verify your API token has write permissions\n"
            "- ✅ Create the issue manually in Jira if needed\n"
        )

    return (
        "⚠ **Failed to create Jira issue:**\n\n"
        "The system attempted to create the Jira issue but encountered an issue.\n\n"
        "**Please check:**\n"
        "- ✅ Your Jira configuration (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)\n"
        "- ✅ API token has write permissions\n"
        "- ✅ Network connectivity to Jira\n"
        "- ✅ Jira project key is correct\n\n"
        "Please try again or create the issue manually in Jira."
    )


def build_jira_rag_document(
    *,
    jira_result: Dict[str, Any],
    backlog_data: Dict[str, Any],
    tool_used: str,
    created_at: str,
) -> str:
    """Create the Jira issue document text used for RAG ingestion."""
    acceptance_criteria = backlog_data.get("acceptance_criteria", "")
    if isinstance(acceptance_criteria, list):
        acceptance_criteria = ", ".join(acceptance_criteria)

    return f"""Jira Issue: {jira_result['key']}
Summary: {backlog_data.get('summary', '')}
Priority: {backlog_data.get('priority', 'Medium')}
Business Value: {backlog_data.get('business_value', '')}
Acceptance Criteria: {acceptance_criteria}
INVEST Analysis: {backlog_data.get('invest_analysis', '')}
Description: {backlog_data.get('description', '')}
Link: {jira_result['link']}
Created: {created_at}
Tool Used: {tool_used}
"""


def build_jira_rag_metadata(
    *,
    jira_result: Dict[str, Any],
    backlog_data: Dict[str, Any],
    created_at: str,
) -> Dict[str, Any]:
    """Create stable Jira metadata for RAG ingestion."""
    return {
        "type": "jira_issue",
        "key": jira_result["key"],
        "title": backlog_data.get("summary", ""),
        "priority": backlog_data.get("priority", "Medium"),
        "link": jira_result["link"],
        "created_at": created_at,
    }


def _is_jira_creation_tool(tool_name: str) -> bool:
    tool_name_lower = (tool_name or "").lower()
    if "confluence" in tool_name_lower or "page" in tool_name_lower:
        return False
    return ("jira" in tool_name_lower or "issue" in tool_name_lower) and "create" in tool_name_lower


def _parse_mcp_result_payload(mcp_result: Any) -> Dict[str, Any]:
    if isinstance(mcp_result, str):
        normalized_result = mcp_result.strip()
        normalized_lower = normalized_result.lower()
        if "timed out" in normalized_lower or "timeout" in normalized_lower:
            raise ValueError(f"MCP tool timeout: {mcp_result}")
        if normalized_result.startswith("Error:"):
            raise ValueError(f"MCP tool error: {normalized_result.replace('Error:', '').strip()}")
        return json.loads(_strip_code_fences(normalized_result))

    if isinstance(mcp_result, dict):
        return mcp_result

    return json.loads(_strip_code_fences(str(mcp_result).strip()))


def _strip_code_fences(payload: str) -> str:
    if not payload.startswith("```"):
        return payload

    lines = payload.split("\n")
    json_lines = [line for line in lines if not line.strip().startswith("```")]
    return "\n".join(json_lines)
