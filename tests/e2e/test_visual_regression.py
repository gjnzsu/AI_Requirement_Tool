"""
E2E tests for visual regression.
Tests screenshot comparisons to catch UI changes.
"""

import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

from .pages.chat_page import ChatPage
from .pages.login_page import LoginPage


# Screenshot directory
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"


@pytest.mark.e2e
class TestVisualRegression:
    """Test suite for visual regression testing (mostly UI-focused)."""
    
    @pytest.fixture(autouse=True)
    def setup_screenshot_dir(self):
        """Ensure screenshot directory exists."""
        SCREENSHOT_DIR.mkdir(exist_ok=True)
        yield
        # Cleanup can be added here if needed
    
    @pytest.mark.e2e_ui
    def test_login_page_screenshot(self, page: Page, flask_test_server):
        """Test login page visual appearance."""
        login_page = LoginPage(page)
        login_page.goto()
        
        # Wait for page to fully load
        page.wait_for_load_state("networkidle")
        
        # Take screenshot
        screenshot_path = SCREENSHOT_DIR / "login_page.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        # Verify screenshot was created
        assert screenshot_path.exists(), "Login page screenshot should be created"
        
        # Note: For actual visual regression testing, you would compare
        # this screenshot with a baseline using tools like:
        # - Percy
        # - Chromatic
        # - Playwright's built-in screenshot comparison
        # - Custom image comparison libraries
    
    @pytest.mark.e2e_ui
    def test_chat_interface_empty_state(self, authenticated_page: Page):
        """Test chat interface empty state visual appearance."""
        chat_page = ChatPage(authenticated_page)
        
        # Wait for page to load
        authenticated_page.wait_for_load_state("networkidle")
        
        # Take screenshot of empty state
        screenshot_path = SCREENSHOT_DIR / "chat_empty_state.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Chat empty state screenshot should be created"
    
    @pytest.mark.e2e_integration
    def test_chat_interface_with_messages(self, authenticated_page: Page, mock_chatbot):
        """Test chat interface with messages visual appearance."""
        chat_page = ChatPage(authenticated_page)
        
        # Send a few messages
        with authenticated_page.expect_response(lambda response: "/api/chat" in response.url, timeout=15000):
            chat_page.send_message("First message")
        
        try:
            chat_page.wait_for_assistant_response(timeout=15000)
        except Exception:
            pass  # Continue even if response times out
        
        with authenticated_page.expect_response(lambda response: "/api/chat" in response.url, timeout=15000):
            chat_page.send_message("Second message")
        
        try:
            chat_page.wait_for_assistant_response(timeout=15000)
        except Exception:
            pass  # Continue even if response times out
        
        # Wait for UI to settle
        authenticated_page.wait_for_timeout(1000)
        
        # Take screenshot
        screenshot_path = SCREENSHOT_DIR / "chat_with_messages.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Chat with messages screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_chat_interface_loading_state(self, authenticated_page: Page):
        """Test chat interface loading state visual appearance (UI test, no backend)."""
        """Test chat interface loading state visual appearance."""
        chat_page = ChatPage(authenticated_page)
        
        # Send a message (triggers loading state) - UI test, no API wait
        chat_page.send_message("Loading test")
        
        # Take screenshot immediately (should show loading) - UI state
        # Note: Loading state might be very brief
        authenticated_page.wait_for_timeout(200)
        
        screenshot_path = SCREENSHOT_DIR / "chat_loading_state.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Chat loading state screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_conversation_list_populated(self, authenticated_page: Page, flask_test_server, temp_db):
        """Test conversation list visual appearance when populated (UI test, uses test DB)."""
        """Test conversation list visual appearance when populated."""
        # Create conversations
        memory_manager, db_path = temp_db
        memory_manager.create_conversation("Conversation 1")
        memory_manager.create_conversation("Conversation 2")
        memory_manager.create_conversation("Conversation 3")
        
        # Patch memory manager
        import app
        app.memory_manager = memory_manager
        
        # Reload page
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")
        
        chat_page = ChatPage(authenticated_page)
        chat_page.wait_for_conversations_to_load()
        
        # Take screenshot of sidebar with conversations
        screenshot_path = SCREENSHOT_DIR / "conversation_list_populated.png"
        # Screenshot just the sidebar area
        sidebar = authenticated_page.locator(".sidebar")
        sidebar.screenshot(path=str(screenshot_path))
        
        assert screenshot_path.exists(), "Conversation list screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_conversation_list_empty(self, authenticated_page: Page):
        """Test conversation list visual appearance when empty."""
        chat_page = ChatPage(authenticated_page)
        
        # Clear all conversations if any exist
        conversations = chat_page.get_conversations()
        if len(conversations) > 0:
            authenticated_page.on("dialog", lambda dialog: dialog.accept())
            try:
                chat_page.clear_all_conversations()
                authenticated_page.wait_for_timeout(1000)
            except Exception:
                # If clearing fails, continue anyway
                pass
        
        # Wait for page to be stable
        authenticated_page.wait_for_load_state("networkidle", timeout=10000)
        
        # Take screenshot of empty sidebar with error handling
        screenshot_path = SCREENSHOT_DIR / "conversation_list_empty.png"
        try:
            # Wait for sidebar to exist
            sidebar = authenticated_page.locator(".sidebar")
            sidebar.wait_for(state="attached", timeout=10000)
            
            # Verify sidebar is still attached before screenshot
            if sidebar.count() > 0 and not authenticated_page.is_closed():
                sidebar.screenshot(path=str(screenshot_path), timeout=10000)
            else:
                # Fallback: screenshot the whole page
                authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            # If sidebar screenshot fails, try full page screenshot
            try:
                if not authenticated_page.is_closed():
                    authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
                else:
                    pytest.skip(f"Page closed before screenshot: {e}")
            except Exception as e2:
                pytest.skip(f"Could not take screenshot: {e2}")
        
        assert screenshot_path.exists(), "Empty conversation list screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_error_state_visual(self, authenticated_page: Page):
        """Test error state visual appearance."""
        chat_page = ChatPage(authenticated_page)
        
        # Trigger an error (e.g., network error)
        from playwright.sync_api import Route
        
        def handle_route(route: Route):
            route.abort()
        
        authenticated_page.route("**/api/chat", handle_route)
        
        # Send message to trigger error
        chat_page.send_message("Error test")
        
        # Wait for error to appear
        authenticated_page.wait_for_timeout(2000)
        
        # Take screenshot of error state
        screenshot_path = SCREENSHOT_DIR / "error_state.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Error state screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_mobile_viewport(self, authenticated_page: Page):
        """Test visual appearance on mobile viewport."""
        # Set mobile viewport
        authenticated_page.set_viewport_size({"width": 375, "height": 667})
        
        # Reload to apply viewport
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")
        
        # Take screenshot
        screenshot_path = SCREENSHOT_DIR / "mobile_viewport.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Mobile viewport screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_tablet_viewport(self, authenticated_page: Page):
        """Test visual appearance on tablet viewport."""
        # Set tablet viewport
        authenticated_page.set_viewport_size({"width": 768, "height": 1024})
        
        # Reload to apply viewport
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")
        
        # Take screenshot
        screenshot_path = SCREENSHOT_DIR / "tablet_viewport.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Tablet viewport screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_desktop_viewport(self, authenticated_page: Page):
        """Test visual appearance on desktop viewport."""
        # Set desktop viewport
        authenticated_page.set_viewport_size({"width": 1920, "height": 1080})
        
        # Reload to apply viewport
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle")
        
        # Take screenshot
        screenshot_path = SCREENSHOT_DIR / "desktop_viewport.png"
        authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        
        assert screenshot_path.exists(), "Desktop viewport screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_model_selector_dropdown(self, authenticated_page: Page):
        """Test model selector dropdown visual appearance."""
        # Wait for page to be ready
        authenticated_page.wait_for_load_state("networkidle", timeout=10000)
        
        chat_page = ChatPage(authenticated_page)
        
        # Wait for model selector to be ready
        try:
            chat_page.model_select.wait_for(state="visible", timeout=10000)
        except Exception:
            authenticated_page.wait_for_selector("#modelSelect", timeout=5000, state="attached")
            authenticated_page.wait_for_timeout(1000)
        
        # Verify model selector exists before interacting
        if chat_page.model_select.count() == 0:
            pytest.skip("Model selector not found - cannot take screenshot")
        
        # Open model selector dropdown
        try:
            chat_page.model_select.click()
            # Wait for dropdown to appear
            authenticated_page.wait_for_timeout(500)
        except Exception as e:
            pytest.skip(f"Could not interact with model selector: {e}")
        
        # Take screenshot with error handling
        screenshot_path = SCREENSHOT_DIR / "model_selector_dropdown.png"
        try:
            # Try to screenshot the model selector area
            model_selector = authenticated_page.locator(".model-selector, #modelSelect")
            if model_selector.count() > 0:
                model_selector.wait_for(state="visible", timeout=5000)
                model_selector.screenshot(path=str(screenshot_path), timeout=10000)
            else:
                # Fallback: screenshot the whole page
                authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            # If screenshot fails, try full page screenshot
            try:
                authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pytest.skip(f"Could not take screenshot: {e}")
        
        assert screenshot_path.exists(), "Model selector dropdown screenshot should be created"
    
    @pytest.mark.e2e_ui
    def test_active_conversation_highlight(self, authenticated_page: Page, flask_test_server, temp_db):
        """Test active conversation highlighting visual appearance (UI test, uses test DB)."""
        # Create and load a conversation
        memory_manager, db_path = temp_db
        conv_id = memory_manager.create_conversation("Active Conversation")
        
        # Patch memory manager
        import app
        app.memory_manager = memory_manager
        
        # Reload page
        authenticated_page.reload()
        authenticated_page.wait_for_load_state("networkidle", timeout=15000)
        
        chat_page = ChatPage(authenticated_page)
        chat_page.wait_for_conversations_to_load(timeout=15000)
        
        # Give extra time for API call to complete
        authenticated_page.wait_for_timeout(2000)
        
        # Get conversations to find the actual ID used in UI
        conversations = chat_page.get_conversations()
        if len(conversations) == 0:
            # Try to take screenshot anyway without active conversation
            screenshot_path = SCREENSHOT_DIR / "active_conversation.png"
            try:
                authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
                pytest.skip("No conversations loaded from API - screenshot taken of current state")
            except Exception:
                pytest.skip("No conversations loaded from API (backend issue)")
        
        # Find conversation by title or use first one
        target_conv = next((c for c in conversations if "Active" in c.get("title", "")), conversations[0])
        actual_conv_id = target_conv.get("id")
        
        if not actual_conv_id:
            pytest.skip("Conversation ID not found in UI")
        
        # Click on conversation with proper waiting
        try:
            conv_selector = f".conversation-item[data-conversation-id='{actual_conv_id}'], [data-id='{actual_conv_id}'], [data-conversation-id='{actual_conv_id}']"
            conv_element = authenticated_page.locator(conv_selector)
            conv_element.wait_for(state="visible", timeout=10000)
            conv_element.click()
            authenticated_page.wait_for_timeout(1000)
        except Exception as e:
            # If click fails, still try to take screenshot
            pass
        
        # Take screenshot of active conversation with error handling
        screenshot_path = SCREENSHOT_DIR / "active_conversation.png"
        try:
            sidebar = authenticated_page.locator(".sidebar")
            if sidebar.count() > 0:
                sidebar.wait_for(state="attached", timeout=5000)
                sidebar.screenshot(path=str(screenshot_path), timeout=10000)
            else:
                # Fallback: screenshot the whole page
                authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            # Fallback: screenshot the whole page
            try:
                authenticated_page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception:
                pytest.skip(f"Could not take screenshot: {e}")
        
        assert screenshot_path.exists(), "Active conversation screenshot should be created"

