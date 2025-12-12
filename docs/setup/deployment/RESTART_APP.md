# How to Restart the Flask App to Enable MCP

## The Issue

The Flask app caches the chatbot instance when it first starts. If you changed `USE_MCP` in the `.env` file after the app was already running, the old value is still cached.

## Solution: Restart the Flask App

1. **Stop the current Flask server:**
   - If running in terminal, press `Ctrl+C`
   - Or close the terminal window

2. **Restart the Flask server:**
   ```powershell
   python app.py
   ```

3. **Verify MCP is enabled:**
   - Look for this message when the app starts:
     ```
     ✓ MCP integration enabled - will initialize on first use
     ```
   - When creating a Jira issue, you should see:
     ```
     ✓ MCP is enabled (USE_MCP=True)
     ```

## Why This Happens

The `get_chatbot()` function in `app.py` creates the chatbot instance once and caches it:

```python
chatbot_instance = None  # Global cache

def get_chatbot():
    global chatbot_instance
    if chatbot_instance is None:  # Only creates once!
        chatbot_instance = Chatbot(...)
    return chatbot_instance
```

When the app first starts, it reads `Config.USE_MCP` and creates the chatbot with that value. Even if you change the `.env` file later, the cached instance still has the old value.

## Quick Fix

After changing `.env`, always restart your Flask app!

