"""Pure keyword-based intent routing helpers for the agent graph."""

import re
from typing import Optional


JIRA_CREATION_KEYWORDS = [
    "create jira",
    "create issue",
    "create ticket",
    "create backlog",
    "create a jira",
    "create an issue",
    "create a ticket",
    "create a backlog",
    "create the jira",
    "create the issue",
    "create the ticket",
    "new jira",
    "new issue",
    "new ticket",
    "new backlog",
    "add jira",
    "add issue",
    "add ticket",
    "make jira",
    "make issue",
    "make ticket",
    "jira ticket",
    "jira issue",
    "jira backlog",
    "open jira",
    "open issue",
    "open ticket",
    "generate jira",
    "generate issue",
    "generate ticket",
    "submit jira",
    "submit issue",
    "submit ticket",
]

JIRA_CREATION_PATTERNS = [
    r"\b(create|make|add|new|open|generate|submit)\s+(a\s+)?(jira|issue|ticket|backlog)",
    r"\b(jira|issue|ticket)\s+(create|creation|ticket|issue)",
    r"pls\s+create\s+(a\s+)?(jira|issue|ticket)",
    r"please\s+create\s+(a\s+)?(jira|issue|ticket)",
]

RAG_KEYWORDS = [
    "knowledge base",
    "document",
    "documentation",
    "documents",
    "guide",
    "guides",
    "tutorial",
    "tutorials",
    "example",
    "examples",
    "sample",
    "samples",
    "what was the",
    "show me the",
    "find the",
    "acceptance criteria",
    "business value",
    "details of",
    "details for",
    "info about",
    "information about",
    "look up",
    "lookup",
    "search for",
    "previous ticket",
    "previous issue",
    "previous jira",
    "created ticket",
    "created issue",
    "created jira",
    "our tickets",
    "our issues",
    "our jiras",
    "ticket details",
    "issue details",
    "jira details",
    "confluence page",
    "wiki page",
]

GENERAL_CHAT_KEYWORDS = [
    "hello",
    "hi",
    "hey",
    "你好",
    "您好",
    "who are you",
    "what are you",
    "how are you",
    "what model",
    "which model",
    "llm model",
    "thanks",
    "thank you",
    "bye",
    "goodbye",
    "help",
    "assist",
    "chat",
    "talk",
]

CONFLUENCE_TOOLING_KEYWORDS = [
    "confluence tool",
    "confluence api",
    "confluence integration",
    "how does confluence",
    "what is confluence tool",
    "confluence background",
    "confluence setup",
    "confluence config",
]

REQUIREMENT_SKILL_KEYWORDS = [
    "requirement lifecycle",
    "turn this into a requirement",
    "help me turn this into a requirement",
    "draft a ticket and docs",
    "draft requirement",
    "requirement analysis",
]

COZE_KEYWORDS = ["ai daily report", "ai daily news", "ai news"]
JIRA_KEY_LOOKUP_PATTERN = r"\b[A-Z]{2,10}-\d+\b"


def detect_keyword_intent(
    user_input: str,
    *,
    rag_service_available: bool,
    jira_available: bool,
    coze_enabled: bool,
) -> Optional[str]:
    """Return a keyword-detected intent, or None when no deterministic route exists."""
    normalized_input = (user_input or "").lower()

    if any(keyword in normalized_input for keyword in CONFLUENCE_TOOLING_KEYWORDS):
        return "general_chat"

    if _matches_coze_intent(normalized_input) and coze_enabled:
        return "coze_agent"

    if any(keyword in normalized_input for keyword in REQUIREMENT_SKILL_KEYWORDS):
        return "requirement_sdlc_agent"

    if jira_available and _matches_jira_creation_intent(normalized_input):
        return "jira_creation"

    if rag_service_available and _matches_jira_lookup_intent(user_input or "", normalized_input):
        return "rag_query"

    if rag_service_available and any(keyword in normalized_input for keyword in RAG_KEYWORDS):
        return "rag_query"

    if any(keyword in normalized_input for keyword in GENERAL_CHAT_KEYWORDS):
        return "general_chat"

    return None


def _matches_coze_intent(normalized_input: str) -> bool:
    if any(keyword in normalized_input for keyword in COZE_KEYWORDS):
        return True

    words = normalized_input.split()
    return "ai" in words and "news" in words


def _matches_jira_creation_intent(normalized_input: str) -> bool:
    if any(keyword in normalized_input for keyword in JIRA_CREATION_KEYWORDS):
        return True

    return any(
        re.search(pattern, normalized_input, re.IGNORECASE)
        for pattern in JIRA_CREATION_PATTERNS
    )


def _matches_jira_lookup_intent(raw_user_input: str, normalized_input: str) -> bool:
    jira_key_match = re.search(JIRA_KEY_LOOKUP_PATTERN, raw_user_input)
    if not jira_key_match:
        return False

    return not _matches_jira_creation_intent(normalized_input)
