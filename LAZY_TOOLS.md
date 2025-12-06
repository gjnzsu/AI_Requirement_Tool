# Lazy Loading for MCP Tools

## Overview

MCP tools (Jira, Confluence) are now loaded **lazily** - they only initialize when actually needed, not on every chatbot creation. This solves dead loop issues and improves startup performance.

## How It Works

### Before (Eager Loading)
- Tools initialized immediately when chatbot is created
- Could hang on network connections (Jira/Confluence)
- Slower startup time
- Dead loops if credentials are invalid

### After (Lazy Loading)
- Tools initialized only when needed
- Fast chatbot startup
- No hanging on initialization
- Tools load automatically when Jira keywords are detected

## Configuration

Add to your `.env` file:

```bash
# Enable/disable MCP tools (default: true)
ENABLE_MCP_TOOLS=true

# Lazy load tools (default: true - recommended)
LAZY_LOAD_TOOLS=true
```

## Usage

### Default Behavior (Lazy Loading Enabled)

```python
from src.chatbot import Chatbot

# Chatbot creates instantly - no tool initialization
chatbot = Chatbot()  # Fast! No Jira/Confluence connection

# Tools initialize automatically when you say "create jira"
response = chatbot.get_response("create jira ticket for new feature")
# Tools are initialized here automatically
```

### Disable Lazy Loading (Eager Loading)

```python
# Initialize tools immediately (not recommended)
chatbot = Chatbot(lazy_load_tools=False)
# Tools connect to Jira/Confluence immediately
```

### Disable MCP Tools Entirely

```python
# Disable tools completely
chatbot = Chatbot(enable_mcp_tools=False)
# No Jira/Confluence functionality
```

## When Tools Are Initialized

Tools are automatically initialized when:

1. **Jira creation keywords detected:**
   - "create jira"
   - "create jira ticket"
   - "create jira issue"
   - "create jira backlog"
   - etc.

2. **Manual initialization:**
   ```python
   chatbot._initialize_tools()  # Force initialization
   ```

## Benefits

✅ **Fast Startup**: Chatbot creates instantly  
✅ **No Dead Loops**: Tools only connect when needed  
✅ **Better Performance**: No unnecessary network calls  
✅ **Graceful Degradation**: Works even if Jira/Confluence are unavailable  

## Example

```python
from src.chatbot import Chatbot

# Fast creation - no tool initialization
chatbot = Chatbot(use_rag=True)

# Normal conversation - no tools needed
response1 = chatbot.get_response("What is Python?")
# Fast response, no tool initialization

# Jira creation - tools initialize automatically
response2 = chatbot.get_response("create jira ticket for bug fix")
# Tools initialize here, then create Jira issue
```

## Troubleshooting

**Q: Tools not initializing when I say "create jira"?**
- Check that `enable_mcp_tools=True` (default)
- Verify Jira credentials are set in `.env`
- Check console for error messages

**Q: Want to disable tools completely?**
```python
chatbot = Chatbot(enable_mcp_tools=False)
```

**Q: Want tools to initialize immediately?**
```python
chatbot = Chatbot(lazy_load_tools=False)
# Not recommended - may cause hanging
```

## Migration

No changes needed! Lazy loading is enabled by default. Your existing code will work faster.

To disable lazy loading (if needed):
```python
# In your code
chatbot = Chatbot(lazy_load_tools=False)

# Or in .env
LAZY_LOAD_TOOLS=false
```

