"""Direct Confluence read adapter for PM status workflows."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests


class DirectConfluenceReadAdapter:
    """Read Confluence pages through the REST API."""

    def __init__(
        self,
        *,
        confluence_url: str,
        auth: Any,
        session: Optional[Any] = None,
    ) -> None:
        self.confluence_url = confluence_url.rstrip("/")
        self.auth = auth
        self.session = session or requests

    def get_page(
        self,
        page_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if page_id:
            url = f"{self.confluence_url}/rest/api/content/{page_id}"
            params = {"expand": "body.storage,_links"}
        elif title:
            url = f"{self.confluence_url}/rest/api/content"
            params = {"title": title, "expand": "body.storage,_links"}
        else:
            return None

        response = self.session.get(url, params=params, auth=self.auth, timeout=(10, 30))
        response.raise_for_status()
        payload = response.json()
        if "results" in payload:
            results = payload.get("results") or []
            payload = results[0] if results else None
        return self._normalize_page(payload) if payload else None

    def search_pages(
        self,
        query: str,
        space_key: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        cql = f'type=page AND text ~ "{query}"'
        if space_key:
            cql = f'space="{space_key}" AND {cql}'
        response = self.session.get(
            f"{self.confluence_url}/rest/api/search",
            params={"cql": cql, "limit": limit},
            auth=self.auth,
            timeout=(10, 30),
        )
        response.raise_for_status()
        results = response.json().get("results") or []
        return [self._normalize_search_result(item) for item in results]

    def _normalize_page(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = payload.get("body", {}).get("storage", {}).get("value", "")
        return {
            "id": str(payload.get("id", "")),
            "title": payload.get("title", ""),
            "url": self._absolute_url(payload.get("_links", {}).get("webui", "")),
            "content": self._html_to_text(body),
        }

    def _normalize_search_result(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        content = payload.get("content") or payload
        return {
            "id": str(content.get("id", "")),
            "title": content.get("title", ""),
            "url": self._absolute_url(content.get("_links", {}).get("webui", "")),
            "content": self._html_to_text(payload.get("excerpt", "")),
        }

    def _absolute_url(self, webui: str) -> str:
        if not webui:
            return ""
        if webui.startswith("http"):
            return webui
        if self.confluence_url.endswith("/wiki") and webui.startswith("/wiki/"):
            return f"{self.confluence_url[:-5]}{webui}"
        return f"{self.confluence_url}{webui}"

    def _html_to_text(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", "", value or "")
        return re.sub(r"\s+", " ", text).strip()
