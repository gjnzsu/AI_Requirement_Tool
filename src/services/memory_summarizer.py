"""
Memory Summarizer for compressing long conversation histories.

This module provides functionality to summarize conversation history
using LLM to maintain context while reducing token usage.
"""

from typing import List, Dict, Optional
from src.llm import LLMRouter, LLMProviderManager


class MemorySummarizer:
    """
    Summarizes conversation history using LLM to compress long conversations.
    """
    
    def __init__(self, llm_provider=None):
        """
        Initialize the memory summarizer.
        
        Args:
            llm_provider: LLM provider instance (optional, will use default if None)
        """
        self.llm_provider = llm_provider
    
    def summarize_conversation(self, messages: List[Dict], 
                             existing_summary: Optional[str] = None) -> str:
        """
        Summarize a conversation or update an existing summary.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            existing_summary: Existing summary to update (optional)
            
        Returns:
            Summary string
        """
        if not messages:
            return "No conversation to summarize."
        
        # Prepare conversation text
        conversation_text = self._format_messages_for_summarization(messages)
        
        # Build summarization prompt
        if existing_summary:
            prompt = f"""
Previous summary of earlier conversation:
{existing_summary}

Recent conversation messages:
{conversation_text}

Please update the summary to include the new information from the recent messages.
Provide a concise summary that captures:
1. Main topics discussed
2. Key decisions or conclusions
3. Important context or details
4. Any action items or next steps

Keep the summary focused and under 200 words.
"""
        else:
            prompt = f"""
Please summarize the following conversation. Provide a concise summary that captures:
1. Main topics discussed
2. Key decisions or conclusions
3. Important context or details
4. Any action items or next steps

Conversation:
{conversation_text}

Keep the summary focused and under 200 words.
"""
        
        system_prompt = (
            "You are a helpful assistant that creates concise, informative summaries "
            "of conversations. Focus on key information and maintain context."
        )
        
        try:
            if self.llm_provider:
                if isinstance(self.llm_provider, LLMProviderManager):
                    summary = self.llm_provider.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=prompt,
                        temperature=0.3,  # Lower temperature for more consistent summaries
                        json_mode=False
                    )
                else:
                    summary = self.llm_provider.generate_response(
                        system_prompt=system_prompt,
                        user_prompt=prompt,
                        temperature=0.3,
                        json_mode=False
                    )
            else:
                # Fallback: simple text-based summary
                summary = self._simple_summarize(messages)
            
            return summary.strip()
            
        except Exception as e:
            # Fallback to simple summary on error
            return self._simple_summarize(messages)
    
    def _format_messages_for_summarization(self, messages: List[Dict]) -> str:
        """Format messages for summarization."""
        formatted = []
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(formatted)
    
    def _simple_summarize(self, messages: List[Dict]) -> str:
        """
        Simple fallback summarization without LLM.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Simple summary string
        """
        if not messages:
            return "No conversation to summarize."
        
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
        
        summary_parts = [
            f"Conversation with {len(user_messages)} user messages and {len(assistant_messages)} assistant responses."
        ]
        
        if user_messages:
            first_topic = user_messages[0].get('content', '')[:100]
            summary_parts.append(f"Started with: {first_topic}...")
        
        return " ".join(summary_parts)
    
    def should_summarize(self, message_count: int, 
                         summary_threshold: int = 30) -> bool:
        """
        Determine if a conversation should be summarized.
        
        Args:
            message_count: Number of messages in conversation
            summary_threshold: Threshold for triggering summarization
            
        Returns:
            True if summarization is recommended
        """
        return message_count > summary_threshold

