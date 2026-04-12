"""Helper service for Atlassian MCP support and content formatting."""

from __future__ import annotations

import concurrent.futures
import json
import re
from typing import Any, Dict, Optional

from src.utils.logger import get_logger


logger = get_logger("chatbot.atlassian_support")


class AtlassianMcpSupportService:
    """Encapsulate Atlassian MCP helper operations used by the chatbot runtime."""

    def __init__(self, *, config: Any, mcp_integration: Any, use_mcp: bool) -> None:
        self.config = config
        self.mcp_integration = mcp_integration
        self.use_mcp = use_mcp

    def get_cloud_id(self) -> Optional[str]:
        """Return the Atlassian cloud ID from MCP or tenant info fallback."""
        if self.use_mcp and self.mcp_integration and self.mcp_integration._initialized:
            try:
                resources_tool = self.mcp_integration.get_tool(
                    "getAccessibleAtlassianResources"
                )
                if resources_tool:
                    payload = self._load_json_payload(resources_tool.invoke(input={}))
                    cloud_id = self._extract_cloud_id(payload)
                    if cloud_id:
                        return cloud_id
            except Exception as error:
                logger.warning("Exception retrieving cloudId via MCP: %s", error)

        jira_url = getattr(self.config, "JIRA_URL", "")
        if jira_url and "atlassian.net" in jira_url:
            try:
                import base64
                import urllib.request

                base_url = jira_url.split("/wiki")[0].split("/browse")[0].rstrip("/")
                request = urllib.request.Request(f"{base_url}/_edge/tenant_info")

                jira_email = getattr(self.config, "JIRA_EMAIL", "")
                jira_api_token = getattr(self.config, "JIRA_API_TOKEN", "")
                if jira_email and jira_api_token:
                    credentials = f"{jira_email}:{jira_api_token}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    request.add_header("Authorization", f"Basic {encoded}")
                request.add_header("Accept", "application/json")

                with urllib.request.urlopen(request, timeout=10) as response:
                    payload = json.loads(response.read().decode())
                    return payload.get("cloudId")
            except Exception as error:
                logger.warning("Exception retrieving cloudId via tenant_info: %s", error)

        return None

    def get_space_id(self, space_key: str, cloud_id: Optional[str] = None) -> Optional[int]:
        """Return a numeric Confluence space id for the given space key."""
        if not space_key:
            return None

        if self.use_mcp and self.mcp_integration and self.mcp_integration._initialized:
            try:
                spaces_tool = self.mcp_integration.get_tool("getConfluenceSpaces")
                if spaces_tool:
                    spaces_args = {}
                    if cloud_id:
                        spaces_args["cloudId"] = cloud_id
                    payload = self._load_json_payload(spaces_tool.invoke(input=spaces_args))
                    for space in self._extract_spaces(payload):
                        if not isinstance(space, dict):
                            continue
                        candidate_key = (
                            space.get("key")
                            or space.get("spaceKey")
                            or space.get("_expandable", {}).get("key")
                        )
                        if candidate_key == space_key:
                            return self._to_optional_int(
                                space.get("id") or space.get("spaceId")
                            )
            except Exception as error:
                logger.warning("Exception retrieving space id via MCP: %s", error)

        confluence_url = getattr(self.config, "CONFLUENCE_URL", "")
        if confluence_url:
            try:
                import base64
                import urllib.request

                base_url = confluence_url.split("/wiki")[0].rstrip("/")
                request = urllib.request.Request(
                    f"{base_url}/wiki/rest/api/space/{space_key}"
                )
                credentials = (
                    f"{getattr(self.config, 'JIRA_EMAIL', '')}:"
                    f"{getattr(self.config, 'JIRA_API_TOKEN', '')}"
                )
                encoded = base64.b64encode(credentials.encode()).decode()
                request.add_header("Authorization", f"Basic {encoded}")
                request.add_header("Content-Type", "application/json")

                with urllib.request.urlopen(request, timeout=10) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    return self._to_optional_int(payload.get("id"))
            except Exception as error:
                logger.warning("Exception retrieving space id via API: %s", error)

        return None

    def retrieve_confluence_page_info(
        self,
        *,
        page_id: Optional[str] = None,
        page_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve Confluence page information via MCP page tools."""
        if not (self.use_mcp and self.mcp_integration is not None):
            return {"success": False, "error": "MCP not enabled"}

        initialization_error = self._ensure_mcp_initialized()
        if initialization_error:
            return {"success": False, "error": initialization_error}

        mcp_tool = self._find_confluence_retrieval_tool()
        if not mcp_tool:
            return {
                "success": False,
                "error": "MCP Confluence retrieval tool not available",
            }

        mcp_args = {}
        if page_id:
            mcp_args["page_id"] = page_id
        if page_title:
            mcp_args["title"] = page_title
        if not mcp_args:
            return {
                "success": False,
                "error": "Either page_id or page_title must be provided",
            }

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(mcp_tool.invoke, input=mcp_args)
                try:
                    result = future.result(timeout=30.0)
                except concurrent.futures.TimeoutError:
                    return {
                        "success": False,
                        "error": "MCP tool call timeout after 30 seconds",
                    }

            if isinstance(result, dict):
                payload = dict(result)
                payload["tool_used"] = "MCP Protocol"
                return payload

            payload = self._load_json_payload(result)
            if isinstance(payload, dict):
                payload["tool_used"] = "MCP Protocol"
                return payload

            if isinstance(result, str):
                return {
                    "success": True,
                    "content": result,
                    "tool_used": "MCP Protocol",
                }

            return {
                "success": False,
                "error": f"Unexpected result type: {type(result)}",
            }
        except Exception as error:
            return {"success": False, "error": f"MCP tool call failed: {error}"}

    def html_to_markdown(self, html_content: str) -> str:
        """Convert Confluence HTML-ish content into a compact markdown form."""
        markdown = html_content
        markdown = re.sub(r"<h1>(.*?)</h1>", r"# \1", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<h2>(.*?)</h2>", r"## \1", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<h3>(.*?)</h3>", r"### \1", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<h4>(.*?)</h4>", r"#### \1", markdown, flags=re.DOTALL)
        markdown = re.sub(r'<a href="([^"]*)">([^<]*)</a>', r"[\2](\1)", markdown)
        markdown = re.sub(r"<strong>(.*?)</strong>", r"**\1**", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<b>(.*?)</b>", r"**\1**", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<em>(.*?)</em>", r"*\1*", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<i>(.*?)</i>", r"*\1*", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<ul>\s*", "", markdown)
        markdown = re.sub(r"</ul>\s*", "", markdown)
        markdown = re.sub(r"<ol>\s*", "", markdown)
        markdown = re.sub(r"</ol>\s*", "", markdown)
        markdown = re.sub(r"<li>(.*?)</li>", r"- \1\n", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<p>(.*?)</p>", r"\1\n\n", markdown, flags=re.DOTALL)
        markdown = re.sub(r"<[^>]+>", "", markdown)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        return markdown.strip()

    def _ensure_mcp_initialized(self) -> Optional[str]:
        if self.mcp_integration._initialized:
            return None

        try:
            import asyncio

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.mcp_integration.initialize())
                try:
                    future.result(timeout=15.0)
                    return None
                except concurrent.futures.TimeoutError:
                    return "MCP initialization timeout"
        except Exception as error:
            return f"MCP initialization failed: {error}"

    def _find_confluence_retrieval_tool(self):
        tool_names = [
            "getConfluencePage",
            "getConfluenceSpaces",
            "getPagesInConfluenceSpace",
            "get_confluence_page",
            "confluence_get_page",
            "get_page",
            "confluence_page_get",
            "read_confluence_page",
            "confluence_read_page",
        ]
        for tool_name in tool_names:
            tool = self.mcp_integration.get_tool(tool_name)
            if not tool:
                continue
            normalized_name = tool.name.lower()
            if "jira" in normalized_name or "issue" in normalized_name:
                continue
            if "confluence" in normalized_name or "page" in normalized_name:
                return tool
        return None

    def _load_json_payload(self, raw_result: Any) -> Any:
        if isinstance(raw_result, dict):
            return raw_result
        if not isinstance(raw_result, str):
            return raw_result
        cleaned = raw_result.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            )
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return raw_result

    def _extract_cloud_id(self, payload: Any) -> Optional[str]:
        if isinstance(payload, dict):
            if payload.get("cloudId"):
                return payload["cloudId"]
            resources = payload.get("resources")
            if isinstance(resources, list) and resources:
                first_resource = resources[0]
                if isinstance(first_resource, dict):
                    return first_resource.get("cloudId") or first_resource.get("id")
        if isinstance(payload, list) and payload:
            first_item = payload[0]
            if isinstance(first_item, dict):
                return first_item.get("cloudId")
        return None

    def _extract_spaces(self, payload: Any):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            spaces = payload.get("results", payload.get("spaces", payload.get("_results", [])))
            if isinstance(spaces, list):
                return spaces
            data = payload.get("data")
            if isinstance(data, list):
                return data
        return []

    def _to_optional_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        match = re.search(r"\d+", str(value))
        return int(match.group()) if match else None
