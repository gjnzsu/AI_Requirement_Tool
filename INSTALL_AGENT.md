# Installing LangGraph Agent Dependencies

## Quick Install

The LangGraph dependencies can take some time to download. Here are your options:

### Option 1: Install All at Once (Recommended)
```powershell
cd generative-ai-chatbot
pip install -r requirements.txt
```

This will install everything including LangGraph. **This may take 5-10 minutes** depending on your internet connection.

### Option 2: Install Agent Dependencies Separately
```powershell
cd generative-ai-chatbot
pip install -r requirements-agent.txt
```

### Option 3: Install Core Packages Only (Faster)
```powershell
cd generative-ai-chatbot
pip install langgraph langchain langchain-core langchain-openai langchain-google-genai
```

## What's Being Installed

The LangGraph agent framework requires:
- **langgraph** (~50-100MB) - Core graph execution engine
- **langchain** (~100-200MB) - LLM integration framework
- **langchain-core** (~20-50MB) - Core abstractions
- **langchain-openai** (~5-10MB) - OpenAI integration
- **langchain-google-genai** (~5-10MB) - Google Gemini integration

**Total download size: ~200-400MB**

## Installation Tips

1. **Use `--no-cache-dir`** if you're low on disk space:
   ```powershell
   pip install langgraph --no-cache-dir
   ```

2. **Install in stages** if connection is slow:
   ```powershell
   pip install langgraph langchain langchain-core
   pip install langchain-openai langchain-google-genai
   ```

3. **Check installation** after completion:
   ```powershell
   python -c "import langgraph; import langchain; print('✓ Installed successfully')"
   ```

## Troubleshooting

### Installation Hanging
If installation seems stuck:
- Press `Ctrl+C` to cancel
- Try installing packages one at a time
- Check your internet connection

### Version Conflicts
If you get version conflicts:
```powershell
pip install --upgrade pip setuptools wheel
pip install langgraph langchain --upgrade
```

### Missing Dependencies
If you see missing dependency errors:
```powershell
pip install typing-extensions pydantic
```

## Verify Installation

After installation, verify it works:
```python
python -c "from langgraph.graph import StateGraph; print('✓ LangGraph ready')"
```

## Next Steps

Once installed, you can test the agent:
```python
from src.chatbot import Chatbot
chatbot = Chatbot(use_agent=True)
response = chatbot.get_response("Hello!")
```

