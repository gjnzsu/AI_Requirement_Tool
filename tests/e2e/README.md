# E2E Web Testing Suite

This directory contains end-to-end (E2E) web tests for the chatbot service UI using Playwright.

## Overview

The E2E test suite covers:
- **Authentication flows**: Login, logout, token management, protected routes
- **Chat interface**: Sending messages, message display, loading states, model switching
- **Conversation management**: Creating, loading, deleting, searching conversations
- **UI components**: Sidebar, model selector, message actions, responsive design
- **Error handling**: Network errors, API errors, rate limits, timeouts
- **Accessibility**: Keyboard navigation, screen reader support, WCAG compliance
- **Visual regression**: Screenshot comparisons for UI changes

## Setup

### Install Dependencies

```bash
pip install -r requirements-test.txt
```

### Install Playwright Browsers

```bash
playwright install
```

Or install only Chromium:

```bash
playwright install chromium
```

## Test Categories

The E2E tests are organized into two categories:

### UI Tests (`@pytest.mark.e2e_ui`)

**Backend-independent tests** that focus on frontend behavior:
- UI component interactions (buttons, inputs, dropdowns)
- Client-side state management (localStorage, UI state)
- Visual appearance and layout
- Accessibility features (keyboard navigation, ARIA labels)
- Responsive design
- Frontend validation

**Benefits:**
- Fast execution (no backend/LLM calls)
- Stable (not affected by backend/LLM instability)
- Can run without backend services
- Focus on frontend correctness

### Integration Tests (`@pytest.mark.e2e_integration`)

**Full-stack tests** that verify end-to-end workflows:
- Authentication flows (login, logout, token management)
- API integration (chat responses, conversation CRUD)
- Backend-dependent features
- Full user workflows

**Benefits:**
- Verify complete system functionality
- Test real API interactions
- Validate backend integration

## Running Tests

### Run All E2E Tests

```bash
pytest tests/e2e/ -m e2e
```

### Run Tests in Parallel (Recommended - 3-4x Faster)

```bash
# Automatically detect optimal worker count (recommended)
pytest tests/e2e/ -m e2e -n auto

# Or specify number of workers (e.g., 4 workers)
pytest tests/e2e/ -m e2e -n 4

# Disable parallel execution (sequential)
pytest tests/e2e/ -m e2e -n 0
```

**Performance Benefits:**
- **3-4x faster** execution time on multi-core machines
- Each worker gets its own browser instance for isolation
- Shared Flask test server across all workers
- Session-scoped authenticated context per worker (faster login)

### Run Only UI Tests (Fast, Backend-Independent)

```bash
# Sequential
pytest tests/e2e/ -m e2e_ui

# Parallel (recommended)
pytest tests/e2e/ -m e2e_ui -n auto
```

### Run Only Integration Tests (Full Stack)

```bash
# Sequential
pytest tests/e2e/ -m e2e_integration

# Parallel (recommended)
pytest tests/e2e/ -m e2e_integration -n auto
```

### Run Specific Test Files

```bash
# Authentication tests (integration)
pytest tests/e2e/test_auth_flows.py

# Chat interface tests (mixed: UI + integration)
pytest tests/e2e/test_chat_interface.py

# Conversation management tests (mixed: UI + integration)
pytest tests/e2e/test_conversations.py

# UI component tests (mostly UI)
pytest tests/e2e/test_ui_components.py

# Accessibility tests (UI)
pytest tests/e2e/test_accessibility.py

# Visual regression tests (mostly UI)
pytest tests/e2e/test_visual_regression.py
```

### Run Tests in Headed Mode (See Browser)

```bash
pytest tests/e2e/ -m e2e --headed
```

### Run Tests with Screenshots on Failure

```bash
pytest tests/e2e/ -m e2e --screenshot=only-on-failure
```

### Run Tests in Debug Mode

```bash
pytest tests/e2e/ -m e2e --pdb
```

## Test Structure

### Page Objects

The tests use the Page Object Model pattern for maintainability:

- `pages/login_page.py`: Login page interactions
- `pages/chat_page.py`: Chat interface interactions

### Fixtures

Key fixtures in `conftest.py`:

- `flask_test_server`: Starts Flask test server on port 5001
- `page`: Creates a new browser page for each test
- `authenticated_page`: Pre-authenticated page session
- `browser`: Playwright browser instance
- `context`: Browser context with base URL configured

## Test Files

- `test_auth_flows.py`: Authentication flow tests
- `test_chat_interface.py`: Chat functionality tests
- `test_conversations.py`: Conversation management tests
- `test_ui_components.py`: UI component tests
- `test_error_handling.py`: Error handling tests
- `test_accessibility.py`: Accessibility tests
- `test_visual_regression.py`: Visual regression tests

## Screenshots

Visual regression tests save screenshots to `tests/e2e/screenshots/`. These are not committed to git (see `.gitignore`).

## CI/CD Integration

To run E2E tests in CI:

1. Install dependencies: `pip install -r requirements-test.txt`
2. Install browsers: `playwright install --with-deps`
3. Run tests: `pytest tests/e2e/ -m e2e`

## Troubleshooting

### Flask Server Fails to Start

If the Flask test server fails to start:
- Check if port 5001 is available
- Ensure all dependencies are installed
- Check that test databases can be created

### Browser Launch Fails

If Playwright browsers fail to launch:
- Run `playwright install` to ensure browsers are installed
- On Linux, you may need system dependencies: `playwright install-deps`

### Tests Timeout

If tests timeout:
- Increase timeout in `pytest.ini` or test file
- Check that Flask server is responding
- Verify network connectivity

## Performance Optimization

### Parallel Execution

The test suite is optimized for parallel execution using `pytest-xdist`:

- **Each worker process** gets its own browser instance (isolated)
- **Shared Flask server** across all workers (session-scoped)
- **Session-scoped authenticated context** per worker (avoids login overhead)
- **Automatic worker detection** with `-n auto` (uses all CPU cores)

**Example:**
```bash
# Fast parallel execution (recommended)
pytest tests/e2e/ -m e2e_ui -n auto

# Expected: 3-4x faster than sequential execution
```

### Fixture Optimization

- `authenticated_context`: Session-scoped, shared across tests in same worker
- `authenticated_page`: Fast page creation from shared context (no login overhead)
- Browser launch args optimized for speed (headless, no GPU, etc.)
- Server startup optimized (faster retry logic)

## Notes

- Tests run against a Flask test server on `http://127.0.0.1:5001`
- Each test gets a fresh browser page (from shared context)
- Test databases are temporary and cleaned up after tests
- Screenshots are saved for visual regression testing
- **UI tests** (`e2e_ui`) are backend-independent and can run without LLM/agent services
- **Integration tests** (`e2e_integration`) require full backend stack including LLM/agent services
- Use `-m e2e_ui` for fast, stable frontend testing during development
- Use `-m e2e_integration` for comprehensive end-to-end validation
- **Parallel execution** (`-n auto`) provides 3-4x speedup on multi-core machines

