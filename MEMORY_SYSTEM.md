# Chat Memory Management System

## Overview

The chatbot now includes a comprehensive memory management system that provides persistent storage, context management, and intelligent summarization for conversations.

## Features

### ✅ Persistent Storage
- **SQLite Database**: All conversations are stored in a SQLite database (`data/chatbot_memory.db`)
- **Automatic Persistence**: Conversations are automatically saved and persist across restarts
- **Metadata Support**: Store custom metadata with conversations and messages

### ✅ Context Window Management
- **Smart Truncation**: Automatically manages context window size
- **Recent Messages**: Keeps recent messages in full context
- **Summary Integration**: Older messages are summarized and included as context

### ✅ Memory Summarization
- **Automatic Summarization**: Long conversations are automatically summarized
- **LLM-Powered**: Uses the configured LLM to create intelligent summaries
- **Incremental Updates**: Summaries are updated as conversations grow

### ✅ Search & Retrieval
- **Full-Text Search**: Search conversations by title or content
- **Conversation Listing**: List all conversations with metadata
- **Efficient Queries**: Indexed database for fast retrieval

## Configuration

Add these environment variables to your `.env` file:

```bash
# Enable/disable persistent memory (default: true)
USE_PERSISTENT_MEMORY=true

# Custom database path (optional, default: data/chatbot_memory.db)
MEMORY_DB_PATH=./data/chatbot_memory.db

# Maximum messages in context window (default: 50)
MAX_CONTEXT_MESSAGES=50

# Threshold for triggering summarization (default: 30)
MEMORY_SUMMARY_THRESHOLD=30
```

## Usage

### In Chatbot Class

```python
from src.chatbot import Chatbot

# Create chatbot with persistent memory
chatbot = Chatbot(
    use_persistent_memory=True,
    conversation_id="conv_12345",  # Optional: specify conversation ID
    max_history=25  # Context window size
)

# Load existing conversation
chatbot.load_conversation("conv_12345")

# Set conversation ID
chatbot.set_conversation_id("conv_12345")

# Get response (automatically saves to persistent memory)
response = chatbot.get_response("Hello!")
```

### In Flask Web App

The Flask app automatically uses persistent memory when enabled. All API endpoints work with persistent storage:

- `GET /api/conversations` - List all conversations
- `GET /api/conversations/<id>` - Get specific conversation
- `POST /api/chat` - Send message (automatically saves)
- `DELETE /api/conversations/<id>` - Delete conversation
- `GET /api/search?q=<query>` - Search conversations

### Direct Memory Manager Usage

```python
from src.services.memory_manager import MemoryManager

# Initialize memory manager
memory = MemoryManager(db_path="./data/chatbot_memory.db")

# Create conversation
memory.create_conversation("conv_123", title="My Conversation")

# Add messages
memory.add_message("conv_123", role="user", content="Hello!")
memory.add_message("conv_123", role="assistant", content="Hi there!")

# Get conversation
conversation = memory.get_conversation("conv_123")

# Get optimized context for LLM
context = memory.get_conversation_context("conv_123", max_messages=50)

# Search conversations
results = memory.search_conversations("python", limit=10)

# Get statistics
stats = memory.get_statistics()
```

## Database Schema

### Conversations Table
- `id` (TEXT PRIMARY KEY): Unique conversation identifier
- `title` (TEXT): Conversation title
- `created_at` (TEXT): ISO timestamp
- `updated_at` (TEXT): ISO timestamp
- `metadata` (TEXT): JSON metadata
- `summary` (TEXT): Conversation summary

### Messages Table
- `id` (INTEGER PRIMARY KEY): Auto-incrementing message ID
- `conversation_id` (TEXT): Foreign key to conversations
- `role` (TEXT): Message role ('user', 'assistant', 'system')
- `content` (TEXT): Message content
- `timestamp` (TEXT): ISO timestamp
- `metadata` (TEXT): JSON metadata

## How It Works

1. **Message Storage**: When a message is sent, it's stored in the database
2. **Context Retrieval**: When building prompts, the system retrieves optimized context
3. **Summarization**: When conversations exceed the threshold, older messages are summarized
4. **Context Building**: Recent messages + summary are used for LLM context

## Benefits

- **Persistent**: Conversations survive server restarts
- **Efficient**: Smart context management reduces token usage
- **Scalable**: Can handle thousands of conversations
- **Searchable**: Find conversations quickly
- **Intelligent**: LLM-powered summarization maintains context

## Migration

If you have existing in-memory conversations, they will continue to work. The system gracefully falls back to in-memory storage if persistent memory is disabled or fails to initialize.

## Troubleshooting

### Database Location
The database is stored in `data/chatbot_memory.db` by default. Make sure the `data` directory exists and is writable.

### Disable Persistent Memory
Set `USE_PERSISTENT_MEMORY=false` in your `.env` file to disable persistent storage and use in-memory storage instead.

### Reset Database
To reset all conversations, delete the `data/chatbot_memory.db` file. The database will be recreated automatically on next startup.

