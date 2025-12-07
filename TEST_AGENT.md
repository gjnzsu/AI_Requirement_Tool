# Testing the LangGraph Agent

## Quick Test

Run the test script:
```powershell
cd generative-ai-chatbot
python test_agent.py
```

## Manual Testing

### 1. Test Basic Agent Import
```python
from src.agent import ChatbotAgent
print("✓ Agent imports successfully!")
```

### 2. Test Chatbot with Agent
```python
from src.chatbot import Chatbot

# Initialize with agent enabled
chatbot = Chatbot(
    provider_name="openai",
    use_agent=True,
    enable_mcp_tools=True
)

# Test general conversation
response = chatbot.get_response("Hello!")
print(response)
```

### 3. Test Intent Detection
```python
# Test Jira creation intent
response = chatbot.get_response("I need to create a Jira ticket")
print(response)

# Test RAG query intent
response = chatbot.get_response("What documents do you have?")
print(response)
```

## Expected Behavior

### With Agent Enabled (`use_agent=True`)
- **Intent Detection**: LLM analyzes user input to determine intent
- **Intelligent Routing**: Automatically routes to appropriate workflow
- **Tool Orchestration**: Uses tools when needed based on intent

### Without Agent (`use_agent=False`)
- **Keyword Matching**: Uses simple keyword detection
- **Manual Routing**: Fixed workflow based on keywords

## Troubleshooting

### Import Errors
```powershell
# Check if packages are installed
pip list | Select-String lang

# Reinstall if needed
pip install --upgrade langgraph langchain langchain-openai
```

### Agent Not Initializing
- Check `.env` file has `OPENAI_API_KEY` or `GEMINI_API_KEY`
- Verify LLM provider is set correctly
- Check error messages in console

### Tools Not Working
- Ensure Jira/Confluence credentials are configured
- Check `enable_mcp_tools=True` in Chatbot initialization
- Verify tools initialize without errors

## Next Steps

Once testing passes:
1. Try creating a Jira issue through natural language
2. Test RAG queries with ingested documents
3. Experiment with different intents

