# Quick Start: Chatbot Web Server

## 🚀 Start the Server

### Option 1: Using PowerShell Script (Easiest)
```powershell
cd generative-ai-chatbot
.\start_server.ps1
```

### Option 2: Direct Python Command
```powershell
cd generative-ai-chatbot
python app.py
```

### Option 3: Using Python Module
```powershell
cd generative-ai-chatbot
python -m flask run
```

## 🌐 Access the Web Interface

Once the server starts, open your browser and go to:
**http://localhost:5000**

## ✅ What You'll See

When the server starts successfully, you should see:
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

## 🎯 Features Available

With the LangGraph agent enabled, you can:

1. **Natural Language Chat**: Just talk normally!
2. **Jira Creation**: Say "I need to create a Jira ticket for..."
3. **RAG Queries**: Ask questions about your documents
4. **Conversation Management**: Create, search, and manage conversations

## 🔧 Troubleshooting

### Port 5000 Already in Use
If you see "Address already in use":
```powershell
# Find what's using port 5000
Get-NetTCPConnection -LocalPort 5000

# Or change the port in app.py (line 319)
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Missing Dependencies
```powershell
pip install -r requirements.txt
```

### Configuration Issues
Make sure your `.env` file has:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4
```

### Agent Not Initializing
If you see warnings about the agent:
- Check that LangGraph is installed: `pip list | Select-String lang`
- The chatbot will fall back to keyword-based routing if agent fails
- Check console output for specific error messages

## 🛑 Stop the Server

Press `Ctrl+C` in the terminal where the server is running.

## 📝 Testing the Agent

Once the server is running, try these in the web interface:

1. **General Chat**: "Hello! How are you?"
2. **Jira Creation**: "I need to create a Jira ticket for user authentication"
3. **RAG Query**: "What documents do you have?" (if documents are ingested)

The agent will intelligently detect your intent and route to the appropriate workflow!

