"""
Page Object for the Chat interface page.
"""

import time
from playwright.sync_api import Page, expect
from typing import List, Optional


class ChatPage:
    """Page Object for the main chat interface."""
    
    def __init__(self, page: Page):
        self.page = page
        self.chat_input = page.locator("#chatInput")
        self.send_button = page.locator("#sendBtn")
        self.chat_messages = page.locator("#chatMessages")
        self.new_chat_button = page.locator("#newChatBtn")
        self.clear_all_button = page.locator("#clearAllBtn")
        self.search_input = page.locator("#searchInput")
        self.conversations_list = page.locator("#conversationsList")
        self.model_select = page.locator("#modelSelect")
        self.logout_button = page.locator("#logoutBtn")
        self.welcome_message = page.locator(".welcome-message")
    
    def goto(self):
        """Navigate to the chat page."""
        self.page.goto("/")
        return self
    
    def type_message(self, message: str):
        """Type a message in the chat input."""
        # Wait for chat input to be ready - try multiple strategies
        try:
            self.chat_input.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#chatInput", timeout=10000, state="attached")
                # Wait a bit more for it to become interactive
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for page to be ready
                self.page.wait_for_load_state("networkidle", timeout=5000)
                self.page.wait_for_timeout(1000)
        
        self.chat_input.fill(message)
        return self
    
    def send_message(self, message: Optional[str] = None):
        """Send a message. If message is provided, types it first."""
        if message:
            self.type_message(message)
        # Wait for send button to be ready - try multiple strategies
        try:
            self.send_button.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#sendBtn", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for page to be ready
                self.page.wait_for_load_state("networkidle", timeout=5000)
                self.page.wait_for_timeout(1000)
        
        self.send_button.click()
        return self
    
    def press_enter_to_send(self):
        """Press Enter key to send message."""
        try:
            self.chat_input.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#chatInput", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for page to be ready
                self.page.wait_for_load_state("networkidle", timeout=5000)
                self.page.wait_for_timeout(1000)
        
        self.chat_input.press("Enter")
        return self
    
    def press_shift_enter(self):
        """Press Shift+Enter for newline."""
        try:
            self.chat_input.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#chatInput", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for page to be ready
                self.page.wait_for_load_state("networkidle", timeout=5000)
                self.page.wait_for_timeout(1000)
        
        self.chat_input.press("Shift+Enter")
        return self
    
    def get_messages(self) -> List[dict]:
        """Get all messages from the chat area."""
        messages = []
        message_elements = self.chat_messages.locator(".message").all()
        
        for msg in message_elements:
            # Messages use CSS classes: "message user" or "message assistant"
            # Check which class is present
            class_name = msg.get_attribute("class") or ""
            if "user" in class_name:
                role = "user"
            elif "assistant" in class_name:
                role = "assistant"
            else:
                role = "unknown"
            
            # Get message content (from .message-content div)
            content_elem = msg.locator(".message-content")
            if content_elem.count() > 0:
                content = content_elem.text_content() or ""
            else:
                content = msg.text_content() or ""
            
            messages.append({"role": role, "content": content})
        
        return messages
    
    def wait_for_assistant_response(self, timeout: int = 30000):
        """Wait for assistant response to appear."""
        # The frontend adds a loading message, then removes it and adds the actual response
        # We need to wait for the final assistant message (not loading)
        
        # Strategy: Wait for assistant message with actual content
        # The loading message has empty content, so we wait for message with content
        
        start_time = time.time()
        max_wait = timeout / 1000.0  # Convert to seconds
        
        while (time.time() - start_time) < max_wait:
            # Check for assistant messages
            assistant_msgs = self.page.locator(".message.assistant").all()
            
            if len(assistant_msgs) > 0:
                # Check if any message has content (not just loading)
                for msg in assistant_msgs:
                    content_elem = msg.locator(".message-content")
                    if content_elem.count() > 0:
                        content = content_elem.text_content() or ""
                        # If content exists and is not just loading indicator, we're done
                        if content and "loading" not in content.lower():
                            return self
                
                # Check if loading message exists
                loading_msg = self.page.locator(".message.assistant.loading")
                if loading_msg.count() == 0:
                    # No loading message, assume we have the final message
                    return self
            
            # Wait a bit before checking again
            self.page.wait_for_timeout(200)
        
        # Timeout - check if we at least have an assistant message
        assistant_msgs = self.page.locator(".message.assistant").all()
        if len(assistant_msgs) == 0:
            raise TimeoutError(f"Assistant message did not appear within {timeout}ms")
        
        # We have a message, even if it might be loading - return anyway
        return self
    
    def is_loading(self) -> bool:
        """Check if there's a loading indicator."""
        return self.page.locator(".message.loading").is_visible()
    
    def create_new_chat(self):
        """Click the new chat button."""
        try:
            self.new_chat_button.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#newChatBtn", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for sidebar to be ready
                self.page.wait_for_selector(".sidebar", timeout=5000, state="visible")
                self.page.wait_for_timeout(1000)
        
        self.new_chat_button.click()
        return self
    
    def clear_all_conversations(self, confirm: bool = True):
        """Clear all conversations. If confirm is True, confirms the dialog."""
        try:
            self.clear_all_button.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#clearAllBtn", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for sidebar to be ready
                self.page.wait_for_selector(".sidebar", timeout=5000, state="visible")
                self.page.wait_for_timeout(1000)
        
        self.clear_all_button.click()
        if confirm:
            # Handle confirmation dialog
            self.page.on("dialog", lambda dialog: dialog.accept())
        return self
    
    def search_conversations(self, query: str):
        """Type in the search input to filter conversations."""
        try:
            self.search_input.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#searchInput", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for sidebar to be ready
                self.page.wait_for_selector(".sidebar", timeout=5000, state="visible")
                self.page.wait_for_timeout(1000)
        
        self.search_input.fill(query)
        return self
    
    def get_conversations(self) -> List[dict]:
        """Get list of conversations from sidebar."""
        conversations = []
        try:
            conv_elements = self.conversations_list.locator(".conversation-item").all()
            
            for conv in conv_elements:
                try:
                    title = conv.locator(".conversation-title").text_content(timeout=5000) or ""
                    conv_id = conv.get_attribute("data-conversation-id", timeout=5000) or ""
                    if conv_id:  # Only add if we got a valid ID
                        conversations.append({"id": conv_id, "title": title})
                except Exception:
                    # If individual conversation fails, skip it
                    continue
        except Exception:
            # If conversations list is not found or empty, return empty list
            pass
        
        return conversations
    
    def click_conversation(self, conversation_id: str):
        """Click on a conversation to load it."""
        self.page.locator(f".conversation-item[data-conversation-id='{conversation_id}']").click()
        return self
    
    def delete_conversation(self, conversation_id: str, confirm: bool = True):
        """Delete a conversation. If confirm is True, confirms the dialog."""
        conv_item = self.page.locator(f".conversation-item[data-conversation-id='{conversation_id}']")
        delete_button = conv_item.locator(".delete-btn")
        delete_button.click()
        
        if confirm:
            # Handle confirmation dialog
            self.page.on("dialog", lambda dialog: dialog.accept())
        
        return self
    
    def select_model(self, model: str):
        """Select a model from the model dropdown."""
        try:
            self.model_select.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#modelSelect", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for sidebar to be ready
                self.page.wait_for_selector(".sidebar", timeout=5000, state="visible")
                self.page.wait_for_timeout(1000)
        
        self.model_select.select_option(model)
        return self
    
    def get_selected_model(self) -> str:
        """Get the currently selected model."""
        try:
            self.model_select.wait_for(state="visible", timeout=10000)
        except Exception:
            # If visible wait fails, try waiting for element to be attached
            try:
                self.page.wait_for_selector("#modelSelect", timeout=10000, state="attached")
                self.page.wait_for_timeout(500)
            except Exception:
                # Last resort: wait for sidebar to be ready
                self.page.wait_for_selector(".sidebar", timeout=5000, state="visible")
                self.page.wait_for_timeout(1000)
        
        return self.model_select.input_value()
    
    def logout(self, confirm: bool = True):
        """Click logout button. If confirm is True, confirms the dialog."""
        self.logout_button.click()
        if confirm:
            # Handle confirmation dialog
            self.page.on("dialog", lambda dialog: dialog.accept())
        return self
    
    def is_welcome_message_visible(self) -> bool:
        """Check if welcome message is visible."""
        return self.welcome_message.is_visible()
    
    def wait_for_conversations_to_load(self, timeout: int = 10000):
        """Wait for conversations to load in the sidebar."""
        # Wait for conversations list element to exist (it might be empty)
        # The element exists even if there are no conversations
        try:
            self.page.wait_for_selector("#conversationsList", timeout=timeout, state="attached")
        except Exception:
            # If selector not found, try waiting for sidebar to be ready
            try:
                self.page.wait_for_selector(".sidebar", timeout=timeout, state="visible")
            except Exception:
                # Last resort: wait a bit for page to load
                self.page.wait_for_timeout(1000)
        return self
    
    def get_notification_text(self) -> Optional[str]:
        """Get text from model change notification if visible."""
        notification = self.page.locator(".model-change-notification")
        if notification.is_visible():
            return notification.text_content()
        return None

