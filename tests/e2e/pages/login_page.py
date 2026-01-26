"""
Page Object for the Login page.
"""

import re
from playwright.sync_api import Page, expect


class LoginPage:
    """Page Object for the login page."""
    
    def __init__(self, page: Page):
        self.page = page
        self.username_input = page.locator("#username")
        self.password_input = page.locator("#password")
        self.login_button = page.locator("#loginBtn")
        self.error_message = page.locator("#errorMessage")
        self.login_form = page.locator("#loginForm")
    
    def goto(self):
        """Navigate to the login page."""
        self.page.goto("/login")
        return self
    
    def fill_username(self, username: str):
        """Fill in the username field."""
        self.username_input.fill(username)
        return self
    
    def fill_password(self, password: str):
        """Fill in the password field."""
        self.password_input.fill(password)
        return self
    
    def click_login(self):
        """Click the login button."""
        self.login_button.click()
        return self
    
    def login(self, username: str, password: str):
        """Perform complete login action."""
        self.fill_username(username)
        self.fill_password(password)
        self.click_login()
        return self
    
    def is_error_visible(self) -> bool:
        """Check if error message is visible."""
        return self.error_message.is_visible()
    
    def get_error_text(self) -> str:
        """Get the error message text."""
        return self.error_message.text_content() or ""
    
    def wait_for_redirect(self, timeout: int = 5000):
        """Wait for redirect after successful login."""
        # Wait for URL to be the root path (not /login)
        # Use regex pattern to match root URL
        import re
        self.page.wait_for_url(re.compile(r".*/$"), timeout=timeout)
        # Also ensure it's not /login
        if "/login" in self.page.url:
            raise AssertionError(f"Still on login page after redirect: {self.page.url}")
        return self
    
    def is_loading(self) -> bool:
        """Check if login button is disabled (loading state)."""
        return self.login_button.is_disabled()

