"""Stable result DTOs returned by application ports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class JiraIssueResult:
    """Normalized issue creation result for application code."""

    success: bool
    key: Optional[str] = None
    link: Optional[str] = None
    error: Optional[str] = None
    tool_used: Optional[str] = None
    raw_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a legacy-style dict payload for existing callers."""
        if self.raw_result is not None:
            payload = dict(self.raw_result)
        else:
            payload = {}

        payload.setdefault("success", self.success)
        if self.key is not None:
            payload.setdefault("key", self.key)
        if self.link is not None:
            payload.setdefault("link", self.link)
        if self.error is not None:
            payload.setdefault("error", self.error)
        if self.tool_used is not None:
            payload.setdefault("tool_used", self.tool_used)
        return payload


@dataclass
class ConfluencePageResult:
    """Normalized Confluence page creation result for application code."""

    success: bool
    page_id: Optional[str] = None
    title: Optional[str] = None
    link: Optional[str] = None
    error: Optional[str] = None
    tool_used: Optional[str] = None
    raw_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a legacy-style dict payload for existing callers."""
        if self.raw_result is not None:
            payload = dict(self.raw_result)
        else:
            payload = {}

        payload.setdefault("success", self.success)
        if self.page_id is not None:
            payload.setdefault("id", self.page_id)
            payload.setdefault("pageId", self.page_id)
        if self.title is not None:
            payload.setdefault("title", self.title)
        if self.link is not None:
            payload.setdefault("link", self.link)
        if self.error is not None:
            payload.setdefault("error", self.error)
        if self.tool_used is not None:
            payload.setdefault("tool_used", self.tool_used)
        return payload

