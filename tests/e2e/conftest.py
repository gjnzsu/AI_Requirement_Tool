"""
Pytest configuration and shared fixtures for E2E web tests using Playwright.
"""

import sys
import os
import tempfile
import secrets
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from playwright.sync_api import Playwright, Browser, BrowserContext, Page, expect

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app import app as flask_app
from src.auth.auth_service import AuthService
from src.auth.user_service import UserService
from src.services.memory_manager import MemoryManager
from config.config import Config


# Flask test server configuration
#
# IMPORTANT (pytest-xdist): each worker is a separate process. If they all bind to the
# same port, workers can accidentally talk to another worker's server (different JWT secret),
# causing "Signature verification failed" and noisy auth logs.
TEST_PORT_BASE = 5001
TEST_HOST = "127.0.0.1"


def _xdist_worker_index() -> int:
    """Return pytest-xdist worker index (gw0 -> 0, gw1 -> 1, ...)."""
    worker = os.environ.get("PYTEST_XDIST_WORKER", "")
    if worker.startswith("gw"):
        try:
            return int(worker[2:])
        except ValueError:
            return 0
    return 0


@pytest.fixture(scope="session")
def flask_test_server():
    """Start Flask test server in a separate thread for E2E tests."""
    worker_idx = _xdist_worker_index()
    test_port = TEST_PORT_BASE + worker_idx
    base_url = f"http://{TEST_HOST}:{test_port}"

    # Configure Flask app for testing
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['DEBUG'] = False
    
    # Import app module to access module-level variables
    import app as app_module
    
    # Import middleware to patch its services
    from src.auth import middleware as auth_middleware
    
    # IMPORTANT: Set test secret key FIRST, before creating any services
    # This ensures all services use the same secret for token creation and verification
    test_secret = secrets.token_urlsafe(32)
    original_secret = Config.JWT_SECRET_KEY
    Config.JWT_SECRET_KEY = test_secret
    
    # Store original values
    original_auth_service = app_module.auth_service
    original_user_service = app_module.user_service
    original_memory_manager = app_module.memory_manager
    
    # Store original middleware services
    original_middleware_auth_service = auth_middleware.auth_service
    original_middleware_user_service = auth_middleware.user_service
    
    # Store original get_chatbot function
    original_get_chatbot = app_module.get_chatbot
    
    # Create temporary database for auth
    temp_auth_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_auth_db.close()
    auth_db_path = temp_auth_db.name
    
    # Create temporary database for memory
    temp_memory_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_memory_db.close()
    memory_db_path = temp_memory_db.name
    
    try:
        # Initialize auth services AFTER setting the secret key
        # This ensures they use the test secret
        auth_service = AuthService()
        user_service = UserService(db_path=auth_db_path)
        memory_manager = MemoryManager(db_path=memory_db_path)
        
        # CRITICAL: Re-create middleware's auth_service with test secret
        # The middleware's auth_service was created at import time with old secret
        # We need to create a new instance with the test secret to match token creation
        auth_middleware.auth_service = AuthService()  # Create new instance with test secret
        auth_middleware.user_service = user_service
        
        # Patch module-level services
        app_module.auth_service = auth_service
        app_module.user_service = user_service
        app_module.memory_manager = memory_manager
        
        # IMPORTANT: Mock get_chatbot() to prevent slow chatbot initialization during tests
        # The chatbot initialization is very slow (MCP, RAG, LangGraph, etc.)
        # and causes test timeouts
        from src.chatbot import Chatbot
        mock_chatbot_instance = Mock(spec=Chatbot)
        mock_chatbot_instance.provider_name = "openai"
        mock_chatbot_instance.get_response = Mock(return_value="Mocked chatbot response")
        mock_chatbot_instance.switch_provider = Mock(return_value=None)
        mock_chatbot_instance.set_conversation_id = Mock(return_value=None)
        mock_chatbot_instance.load_conversation = Mock(return_value=True)
        mock_chatbot_instance.conversation_history = []
        mock_chatbot_instance.memory_manager = memory_manager
        
        # Patch get_chatbot function to return mock (original_get_chatbot already stored above)
        app_module.chatbot_instance = mock_chatbot_instance
        def mock_get_chatbot():
            return mock_chatbot_instance
        app_module.get_chatbot = mock_get_chatbot
        
        # Create test user
        test_user = user_service.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        # Start Flask server in a thread
        def run_server():
            # Enable threaded mode so the dev server can handle concurrent requests
            # (especially important when running Playwright tests in parallel).
            flask_app.run(host=TEST_HOST, port=test_port, debug=False, use_reloader=False, threaded=True)
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start (optimized for faster startup)
        import urllib.request
        import urllib.error
        max_retries = 15  # Reduced from 30
        for i in range(max_retries):
            try:
                req = urllib.request.Request(f"{base_url}/login")
                response = urllib.request.urlopen(req, timeout=0.5)  # Reduced timeout
                if response.getcode() in [200, 302]:
                    break
            except Exception:
                if i < max_retries - 1:
                    time.sleep(0.2)  # Reduced from 0.5s
                else:
                    raise Exception("Flask test server failed to start")
        
        yield {
            'base_url': base_url,
            'port': test_port,
            'auth_service': auth_service,
            'user_service': user_service,
            'memory_manager': memory_manager,
            'test_user': test_user,
            'test_secret': test_secret
        }
        
    finally:
        # Restore original values
        Config.JWT_SECRET_KEY = original_secret
        app_module.auth_service = original_auth_service
        app_module.user_service = original_user_service
        app_module.memory_manager = original_memory_manager
        
        # Restore middleware services
        auth_middleware.auth_service = original_middleware_auth_service
        auth_middleware.user_service = original_middleware_user_service
        
        # Restore get_chatbot function
        app_module.get_chatbot = original_get_chatbot
        app_module.chatbot_instance = None
        
        # Cleanup temp databases
        try:
            if os.path.exists(auth_db_path):
                os.unlink(auth_db_path)
            if os.path.exists(memory_db_path):
                os.unlink(memory_db_path)
        except Exception:
            pass


@pytest.fixture(scope="session")
def playwright() -> Playwright:
    """Initialize Playwright."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Browser launch arguments for Playwright (optimized for speed)."""
    return {
        "headless": True,  # Run in headless mode for CI
        "slow_mo": 0,  # Add delay between actions (0 = no delay)
        "args": [
            "--disable-dev-shm-usage",  # Faster on Linux, prevents crashes
            "--disable-gpu",  # Faster on headless
            "--no-sandbox",  # Faster (safe in test environment)
            "--disable-setuid-sandbox",  # Faster
            "--disable-web-security",  # Faster (safe in test environment)
            "--disable-features=IsolateOrigins,site-per-process",  # Faster
        ]
    }


@pytest.fixture(scope="session")
def browser(playwright: Playwright, browser_type_launch_args):
    """Launch browser for E2E tests."""
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser, flask_test_server):
    """Create a new browser context for each test."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        base_url=flask_test_server['base_url']
    )
    # Standardize timeouts to avoid flaky "Page.goto Timeout 10000ms exceeded" errors
    # from overly-aggressive per-call timeouts elsewhere.
    context.set_default_timeout(15000)
    context.set_default_navigation_timeout(30000)
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Page:
    """Create a new page for each test."""
    page = context.new_page()
    # Keep navigation timeouts consistent across tests/page objects
    page.set_default_timeout(15000)
    page.set_default_navigation_timeout(30000)
    yield page
    
    # Take screenshot on test failure
    # Check if test failed using pytest's request fixture
    # Note: This requires the request fixture, but we can't add it here
    # Instead, we'll use a hook (see below)
    
    page.close()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture screenshots on test failure."""
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        # Get the page fixture if available
        if "page" in item.funcargs:
            try:
                page = item.funcargs["page"]
                screenshot_dir = Path(__file__).parent / "screenshots"
                screenshot_dir.mkdir(exist_ok=True)
                
                # Create a unique filename based on test name
                test_name = item.name.replace("::", "_").replace("/", "_")
                screenshot_path = screenshot_dir / f"failure_{test_name}.png"
                
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"\n[SCREENSHOT] Test failure screenshot saved to: {screenshot_path}")
            except Exception as e:
                print(f"\n[WARNING] Failed to capture screenshot on test failure: {e}")


@pytest.fixture(scope="session")
def authenticated_context(browser: Browser, flask_test_server):
    """
    Create a shared authenticated browser context for the session (per worker).
    This avoids login overhead for each test when running in parallel.
    Each pytest-xdist worker gets its own authenticated context.
    """
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        base_url=flask_test_server['base_url']
    )
    
    # Login once for the session (per worker)
    page = context.new_page()
    auth_token = None
    auth_user = None
    
    try:
        page.goto("/login", wait_until="domcontentloaded", timeout=30000)
        # Wait for form elements to be ready
        page.wait_for_selector("#username", timeout=5000)
        page.wait_for_selector("#password", timeout=5000)
        page.fill("#username", "testuser")
        page.fill("#password", "testpassword123")
        page.click("#loginBtn")
        page.wait_for_url("**/", timeout=30000)
        # Wait for page to be fully loaded
        page.wait_for_load_state("networkidle", timeout=30000)
        
        # Extract auth token and user from localStorage
        # This is critical - we need to store these to inject into new pages
        # Wait a bit for localStorage to be set by JavaScript
        page.wait_for_timeout(500)
        
        try:
            auth_token = page.evaluate("localStorage.getItem('chatbot_auth_token')")
            auth_user = page.evaluate("localStorage.getItem('chatbot_user')")
            
            # Verify token was extracted successfully
            if not auth_token:
                # If token is None, wait a bit more and try again
                page.wait_for_timeout(1000)
                auth_token = page.evaluate("localStorage.getItem('chatbot_auth_token')")
                auth_user = page.evaluate("localStorage.getItem('chatbot_user')")
            
            if not auth_token:
                raise Exception("Failed to extract auth token from localStorage after login")
                
        except Exception as e:
            # If localStorage access fails, log error
            print(f"[ERROR] Could not extract auth token from localStorage: {e}")
            # Try to get token from page context as fallback
            try:
                # Check if we can get it from the page's JavaScript context
                auth_token = page.evaluate("() => { return window.localStorage ? window.localStorage.getItem('chatbot_auth_token') : null; }")
                auth_user = page.evaluate("() => { return window.localStorage ? window.localStorage.getItem('chatbot_user') : null; }")
            except Exception:
                pass
            
            if not auth_token:
                raise Exception("Authentication token extraction failed - cannot proceed with tests")
                
    finally:
        page.close()
    
    # Verify we have a valid token before storing
    if not auth_token or auth_token == "null" or auth_token == "undefined":
        raise Exception(f"Invalid auth token extracted: {auth_token}")
    
    # Store auth data in context for later use
    context._auth_token = auth_token
    context._auth_user = auth_user
    
    yield context
    
    # Cleanup
    try:
        context.close()
    except Exception:
        pass


@pytest.fixture(scope="function")
def authenticated_page(authenticated_context: BrowserContext):
    """
    Create an authenticated page from the shared session context.
    Much faster than logging in for each test.
    """
    page = authenticated_context.new_page()
    
    # CRITICAL: Inject auth token into localStorage BEFORE navigation
    # This prevents the JavaScript redirect to /login
    auth_token = getattr(authenticated_context, '_auth_token', None)
    auth_user = getattr(authenticated_context, '_auth_user', None)
    
    if not auth_token:
        raise Exception("No auth token available in authenticated_context - cannot create authenticated page")
    
    # Escape the token/user for JavaScript (handle quotes and special chars)
    import json
    auth_token_escaped = json.dumps(auth_token)
    auth_user_escaped = json.dumps(auth_user) if auth_user else "null"
    
    # Set localStorage before navigating using add_init_script
    # This runs before any page JavaScript executes
    page.add_init_script(f"""
        (function() {{
            try {{
                // IMPORTANT: If we're navigating to the login page (e.g., after logout),
                // do NOT inject the auth token. Otherwise tests like logout will
                // immediately re-authenticate and bounce back to "/".
                if (window.location && window.location.pathname && window.location.pathname.includes('/login')) {{
                    return;
                }}
                const token = {auth_token_escaped};
                const user = {auth_user_escaped};
                if (token && token !== 'null' && token !== 'undefined') {{
                    window.localStorage.setItem('chatbot_auth_token', token);
                    if (user && user !== 'null' && user !== 'undefined') {{
                        window.localStorage.setItem('chatbot_user', user);
                    }}
                    console.log('[Test] Auth token injected into localStorage');
                }} else {{
                    console.error('[Test] Invalid token value:', token);
                }}
            }} catch(e) {{
                console.error('[Test] Failed to set localStorage:', e);
            }}
        }})();
    """)
    
    # Navigate to main page and wait for it to be ready
    try:
        # Navigate and wait for load
        page.goto("/", wait_until="domcontentloaded", timeout=30000)
        
        # Wait for network to be idle (ensures JS has loaded)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            # If networkidle times out, wait a bit more for JS to execute
            page.wait_for_timeout(1000)
        
        # Verify token is actually in localStorage after navigation
        try:
            stored_token = page.evaluate("localStorage.getItem('chatbot_auth_token')")
            if not stored_token or stored_token != auth_token:
                # Token not set correctly, try to set it again
                page.evaluate(f"""
                    localStorage.setItem('chatbot_auth_token', {auth_token_escaped});
                    if ({auth_user_escaped} && {auth_user_escaped} !== 'null') {{
                        window.localStorage.setItem('chatbot_user', {auth_user_escaped});
                    }}
                """)
                # Reload page
                page.reload(wait_until="domcontentloaded", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=30000)
        except Exception as e:
            print(f"[WARNING] Could not verify token in localStorage: {e}")
        
        # Check if we got redirected to login (shouldn't happen now, but check anyway)
        if "/login" in page.url:
            # If redirected, try to set localStorage again and reload
            try:
                page.evaluate(f"""
                    localStorage.setItem('chatbot_auth_token', {auth_token_escaped});
                    if ({auth_user_escaped} && {auth_user_escaped} !== 'null') {{
                        window.localStorage.setItem('chatbot_user', {auth_user_escaped});
                    }}
                """)
                page.reload(wait_until="domcontentloaded", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                print(f"[WARNING] Failed to fix login redirect: {e}")
        
        # Wait for key elements to be present - try multiple selectors
        # The page might have chatInput, sidebar, or welcome message
        selectors_to_try = [
            "#chatInput",
            ".sidebar",
            "#conversationsList",
            ".welcome-message",
            "body"  # Fallback - at least body should exist
        ]
        
        element_found = False
        for selector in selectors_to_try:
            try:
                page.wait_for_selector(selector, timeout=5000, state="visible")
                element_found = True
                break
            except Exception:
                continue
        
        if not element_found:
            # Last resort: wait a bit more and hope page loads
            page.wait_for_timeout(2000)
            
    except Exception as e:
        # If navigation fails, log but continue - some tests might handle this
        print(f"[WARNING] Page navigation issue: {e}")
        # Try to wait anyway
        try:
            page.wait_for_timeout(2000)
        except Exception:
            pass
    
    yield page
    
    # Clear state but keep authentication (context-level cookies persist)
    # Safely clear localStorage - handle case where page might be closed
    try:
        if not page.is_closed():
            # Check if page is still valid before accessing localStorage
            page.evaluate("() => { try { localStorage.clear(); } catch(e) {} }")
    except Exception:
        # Ignore errors if page is already closed or in invalid state
        pass
    
    # Close page safely
    try:
        if not page.is_closed():
            page.close()
    except Exception:
        # Ignore errors if page is already closed
        pass


@pytest.fixture(scope="function")
def authenticated_page_legacy(page: Page, flask_test_server):
    """
    Legacy authenticated page fixture (full login per test).
    Use authenticated_page instead for better performance.
    Kept for backward compatibility with tests that need isolated auth.
    """
    # Navigate to login page
    page.goto("/login", wait_until="domcontentloaded", timeout=10000)
    
    # Fill in login form
    page.fill("#username", "testuser")
    page.fill("#password", "testpassword123")
    
    # Submit form
    page.click("#loginBtn")
    
    # Wait for redirect to main page
    page.wait_for_url("**/", timeout=5000)
    
    yield page
    
    # Clear localStorage on cleanup - safely handle errors
    try:
        if not page.is_closed():
            page.evaluate("localStorage.clear()")
    except Exception:
        # Ignore errors if page is already closed or in invalid state
        pass


@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    memory_manager = MemoryManager(db_path=db_path)
    
    yield memory_manager, db_path
    
    # Cleanup
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def sample_conversation():
    """Create a sample conversation dictionary."""
    return {
        'id': 'test_conv_123',
        'title': 'Test Conversation',
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00',
        'messages': [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ],
        'message_count': 2
    }


@pytest.fixture(scope="function")
def sample_conversations():
    """Create a list of sample conversations."""
    return [
        {
            'id': 'conv_1',
            'title': 'First Conversation',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T01:00:00',
            'message_count': 5
        },
        {
            'id': 'conv_2',
            'title': 'Second Conversation',
            'created_at': '2024-01-02T00:00:00',
            'updated_at': '2024-01-02T02:00:00',
            'message_count': 3
        },
        {
            'id': 'conv_3',
            'title': 'Third Conversation',
            'created_at': '2024-01-03T00:00:00',
            'updated_at': '2024-01-03T03:00:00',
            'message_count': 1
        }
    ]


@pytest.fixture(scope="function", autouse=True)
def reset_global_chatbot():
    """Reset global chatbot instance before each test."""
    import app
    app.chatbot_instance = None
    yield
    app.chatbot_instance = None


@pytest.fixture(scope="function", autouse=True)
def reset_global_memory_manager():
    """Reset global memory manager before each test."""
    import app
    original_memory_manager = app.memory_manager
    yield
    app.memory_manager = original_memory_manager


@pytest.fixture(scope="function")
def mock_chatbot():
    """Create a mock Chatbot instance for E2E tests."""
    from src.chatbot import Chatbot
    
    chatbot = Mock(spec=Chatbot)
    chatbot.provider_name = "openai"
    chatbot.get_response = Mock(return_value="Mocked chatbot response")
    chatbot.switch_provider = Mock(return_value=None)
    chatbot.set_conversation_id = Mock(return_value=None)
    chatbot.load_conversation = Mock(return_value=True)
    chatbot.conversation_history = []
    chatbot.memory_manager = None
    
    # Patch the global chatbot instance
    import app
    with patch.object(app, 'chatbot_instance', chatbot):
        yield chatbot

