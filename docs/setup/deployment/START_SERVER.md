# How to Start the Chatbot Server

## Option 1: Web UI Server (Recommended)

Start the Flask web server for the modern web interface:

```bash
cd generative-ai-chatbot
python app.py
```

**Output:**
```
======================================================================
🤖 Chatbot Web UI
======================================================================
Provider: openai
Model: gpt-4.1

Starting web server...
Open your browser and navigate to: http://localhost:5000
======================================================================
 * Running on http://0.0.0.0:5000
```

Then open your browser and visit: **http://localhost:5000**

### Features:
- Modern web interface
- Conversation management
- Jira creation support
- Search functionality

---

## Option 2: Command Line Interface

Start the chatbot in command line mode:

```bash
cd generative-ai-chatbot
python src/chatbot.py
```

**Output:**
```
Initializing chatbot...
Creating chatbot instance...
✓ Initialized LLM provider: openai (gpt-4.1)
Starting chatbot...
======================================================================
🤖 LLM-Powered Chatbot
======================================================================
Provider: openai
Model: gpt-4.1
Temperature: 0.7
Max History: 10 turns

Commands:
  - Type your message and press Enter
  - Type 'bye', 'exit', or 'quit' to end the conversation
  - Type '/clear' to clear conversation history
  - Type '/history' to see conversation summary
======================================================================

Chatbot: Hello! I'm ready to chat. How can I help you today?

You: 
```

---

## Prerequisites

Before starting, make sure:

1. **Dependencies are installed:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration is set** (`.env` file or environment variables):
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-api-key
   OPENAI_MODEL=gpt-4.1
   
   # For Jira functionality:
   JIRA_URL=https://yourcompany.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-api-token
   JIRA_PROJECT_KEY=PROJ
   ```

---

## Quick Start Commands

### Windows PowerShell:
```powershell
cd C:\SourceCode\GenAIChatbot\generative-ai-chatbot
python app.py
```

### Linux/Mac:
```bash
cd generative-ai-chatbot
python app.py
```

---

## Troubleshooting

### Port Already in Use
If port 5000 is busy, change it in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change port
```

### Module Not Found
Install missing dependencies:
```bash
pip install flask flask-cors
```

### Configuration Errors
Check your `.env` file or environment variables are set correctly.

---

## Using Jira Creation Feature

Once the server is running, you can create Jira issues by saying:

- "create the jira"
- "create jira"
- "create a jira ticket"
- "make a jira"

The chatbot will analyze the conversation context and create a Jira backlog item with:
- Summary
- Business Value
- Acceptance Criteria
- Priority
- INVEST Analysis

