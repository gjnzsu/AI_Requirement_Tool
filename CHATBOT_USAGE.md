# LLM-Powered Chatbot Usage Guide

## Overview

The enhanced chatbot now uses your multi-provider LLM infrastructure (OpenAI, Gemini, DeepSeek) to provide intelligent conversational responses with conversation memory.

## Features

- ✅ **Multi-Provider Support**: Works with OpenAI, Google Gemini, or DeepSeek
- ✅ **Conversation Memory**: Maintains context across multiple turns (configurable)
- ✅ **Automatic Fallback**: Falls back to backup providers if primary fails
- ✅ **Configurable**: Customizable system prompts, temperature, and history length
- ✅ **Interactive Commands**: Built-in commands for managing conversations

## Quick Start

### 1. Set Up Environment Variables

Make sure you have your LLM provider configured in your `.env` file or environment variables:

```bash
# Choose your provider
LLM_PROVIDER=gemini  # Options: 'openai', 'gemini', 'deepseek'

# Set the API key for your chosen provider
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-pro-latest

# Or for OpenAI:
# OPENAI_API_KEY=your-api-key-here
# OPENAI_MODEL=gpt-3.5-turbo

# Or for DeepSeek:
# DEEPSEEK_API_KEY=your-api-key-here
# DEEPSEEK_MODEL=deepseek-chat
```

### 2. Run the Chatbot

```bash
python src/chatbot.py
```

### 3. Start Chatting!

The chatbot will greet you and you can start having conversations. Type your messages and press Enter.

## Commands

- **Normal conversation**: Just type your message
- **`/clear`**: Clear conversation history
- **`/history`**: Show conversation summary
- **`bye`, `exit`, `quit`**: End the conversation

## Example Session

```
======================================================================
🤖 LLM-Powered Chatbot
======================================================================
Provider: gemini
Model: gemini-pro-latest
Temperature: 0.7
Max History: 10 turns

Commands:
  - Type your message and press Enter
  - Type 'bye', 'exit', or 'quit' to end the conversation
  - Type '/clear' to clear conversation history
  - Type '/history' to see conversation summary
======================================================================

Chatbot: Hello! I'm an AI assistant powered by Google's Gemini model. I'm here to help answer questions, have conversations, and assist with various tasks. How can I help you today?

You: What is Python?

Chatbot: Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991. Python emphasizes code readability and allows developers to express concepts in fewer lines of code than languages like C++ or Java.

You: Can you write a simple hello world program?

Chatbot: Sure! Here's a simple "Hello, World!" program in Python:

```python
print("Hello, World!")
```

That's it! Just one line. You can save this in a file (e.g., `hello.py`) and run it with `python hello.py`.

You: /history

Chatbot: Conversation has 2 turn(s) in history.

You: bye

Chatbot: Goodbye! It was great chatting with you. Have a wonderful day!
```

## Programmatic Usage

You can also use the chatbot programmatically in your Python code:

```python
from src.chatbot import Chatbot
from config.config import Config

# Create chatbot instance
chatbot = Chatbot(
    provider_name='gemini',  # or None to use Config.LLM_PROVIDER
    use_fallback=True,        # Enable automatic fallback
    temperature=0.7,         # Creativity level (0.0-1.0)
    max_history=10           # Number of conversation turns to remember
)

# Get a response
response = chatbot.get_response("What is machine learning?")
print(response)

# Clear history
chatbot.clear_history()

# Get history summary
print(chatbot.get_history_summary())
```

## Configuration Options

### Temperature
- **0.0-0.3**: More focused, deterministic responses
- **0.4-0.7**: Balanced (recommended)
- **0.8-1.0**: More creative, varied responses

### Max History
Controls how many conversation turns are kept in memory:
- **Small (5-10)**: Good for focused conversations, lower memory usage
- **Medium (10-20)**: Balanced context retention
- **Large (20+)**: Better for long, complex conversations

### System Prompt
Customize the chatbot's personality and behavior:

```python
chatbot = Chatbot(
    system_prompt="You are a helpful coding assistant specializing in Python.",
    temperature=0.5
)
```

## Troubleshooting

### "No API key found"
- Make sure you've set the appropriate API key environment variable
- Check that `LLM_PROVIDER` matches the provider you want to use
- Verify your `.env` file is in the project root

### "Failed to initialize LLM provider"
- Check your API key is valid
- Verify the model name is correct for your provider
- Check your internet connection
- Review provider-specific requirements (e.g., Gemini proxy settings)

### Provider-Specific Issues

**Gemini**: If you're behind a proxy, set `GEMINI_PROXY` environment variable or use `HTTP_PROXY`/`HTTPS_PROXY`.

**OpenAI**: Ensure your API key has sufficient credits and the model name is correct.

**DeepSeek**: Verify your API key and model name are correct.

## Advanced: Fallback Providers

The chatbot can automatically fall back to backup providers if the primary one fails:

```python
chatbot = Chatbot(
    provider_name='openai',
    use_fallback=True  # Will try Gemini or DeepSeek if OpenAI fails
)
```

Fallback providers are automatically detected from available API keys in your configuration.

## Next Steps

- Try different providers and compare responses
- Experiment with temperature settings
- Customize the system prompt for specific use cases
- Integrate the chatbot into your own applications

