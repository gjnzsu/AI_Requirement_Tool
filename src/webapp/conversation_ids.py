"""Conversation ID helpers shared by chat and conversation routes."""

from datetime import datetime


def generate_conversation_id() -> str:
    """Generate a unique conversation ID."""
    return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
