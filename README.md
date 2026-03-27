# Generative AI Chatbot

An advanced AI-powered chatbot with LangGraph agent framework, MCP (Model Context Protocol) integration, RAG (Retrieval-Augmented Generation), and Jira/Confluence tools. Supports multiple LLM providers with intelligent intent detection and automated Jira issue creation.

## 🚀 Key Features

### Core Capabilities
- **LangGraph Agent Framework** - Intelligent agent with intent detection and tool orchestration
- **MCP Integration** - Model Context Protocol support for Jira and Confluence operations
- **RAG Service** - Retrieval-Augmented Generation with vector embeddings and caching
- **Multi-Provider LLM** - OpenAI, Google Gemini, DeepSeek with automatic fallback
- **Coze Platform Integration** - ByteDance Coze agent support via cozepy SDK with configurable timeout
- **Intent Detection** - Automatic detection of user intents (general chat, Jira creation, etc.)
- **Jira Integration** - Create and manage Jira issues via MCP or custom tools
- **Conversation Memory** - Persistent conversation history with summarization
- **Modern Web UI** - Beautiful, responsive chat interface

### Advanced Features
- **Lazy Tool Loading** - Tools initialized only when needed
- **Error Recovery** - Automatic fallback mechanisms
- **Comprehensive Logging** - Detailed logging for debugging and monitoring
- **Integration Tests** - Full test suite for MCP and agent functionality

## 📁 Project Structure

```
generative-ai-chatbot
├── src/
│   ├── agent/              # LangGraph agent framework
│   │   └── agent_graph.py  # Agent graph with intent detection
│   ├── chatbot.py          # Main chatbot class
│   ├── llm/                # Multi-provider LLM infrastructure
│   │   ├── base_provider.py
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   ├── deepseek_provider.py
│   │   └── router.py
│   ├── mcp/                # MCP integration
│   │   ├── mcp_client.py   # MCP client and manager
│   │   ├── mcp_integration.py  # MCP tool integration
│   │   └── jira_mcp_server.py # Custom Jira MCP server
│   ├── rag/                # RAG service
│   │   ├── rag_service.py
│   │   ├── vector_store.py
│   │   ├── embedding_generator.py
│   │   ├── document_loader.py
│   │   └── rag_cache.py
│   ├── tools/              # Custom tools
│   │   ├── jira_tool.py
│   │   └── confluence_tool.py
│   ├── services/          # Services
│   │   ├── jira_maturity_evaluator.py
│   │   ├── memory_manager.py
│   │   └── memory_summarizer.py
│   └── utils/
│       └── helpers.py
├── config/
│   └── config.py          # Configuration management
├── tests/                 # Test suite
│   ├── unit/             # Unit tests (isolated components)
│   ├── integration/     # Integration tests (component interactions)
│   │   ├── mcp/         # MCP integration tests
│   │   ├── rag/         # RAG integration tests
│   │   ├── agent/       # Agent framework tests
│   │   ├── llm/         # LLM provider tests
│   │   └── memory/      # Memory system tests
│   ├── e2e/             # End-to-end tests
│   └── fixtures/        # Test fixtures and utilities
├── web/                  # Web UI frontend
│   ├── templates/
│   └── static/
├── app.py                # Flask web server
├── requirements.txt     # Python dependencies
├── pytest.ini          # Pytest configuration
├── run_tests.py         # Test runner script
└── README.md            # This file
```

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd generative-ai-chatbot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# LLM Provider Configuration
LLM_PROVIDER=openai  # Options: 'openai', 'gemini', 'deepseek'
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-pro
DEEPSEEK_API_KEY=your-deepseek-api-key

# Jira Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=PROJ

# MCP Configuration
USE_MCP=true  # Enable MCP integration

# RAG Configuration (optional)
RAG_ENABLE_CACHE=true
RAG_CACHE_TTL_HOURS=24
```

**Windows PowerShell:**
```powershell
.\set-env.ps1
```

### 4. Run the Application

**Web UI (Recommended):**
```bash
python app.py
```
Then open `http://localhost:5000` in your browser.

**Command Line:**
```bash
python src/chatbot.py
```

## 🎯 Usage Examples

### General Chat
```
You: What is Python?
Chatbot: Python is a high-level programming language...
```

### Create Jira Issue
```
You: Create a new Jira issue about "Add Redis cache for RAG service"
Chatbot: I'll create a Jira issue for you...
✅ Created issue SCRUM-123 via MCP tool
Link: https://yourcompany.atlassian.net/browse/SCRUM-123
```

### Intent Detection
The agent automatically detects user intents:
- **General Chat** - Regular conversation
- **Jira Creation** - Creating Jira issues
- **Question Answering** - Using RAG for context-aware responses

## 🔧 MCP Integration

### Overview

The chatbot uses MCP (Model Context Protocol) to integrate with external tools like Jira and Confluence. MCP provides a standardized way to connect AI agents with external services.

### Features

- **Custom Jira MCP Server** - Python-based MCP server for Jira operations
- **Tool Wrapper** - LangChain-compatible tool wrappers for MCP tools
- **Automatic Fallback** - Falls back to custom tools if MCP is unavailable
- **Lazy Initialization** - MCP tools initialized only when needed

### Enabling MCP

1. Set `USE_MCP=true` in your `.env` file
2. Ensure Jira credentials are configured
3. Restart the application

The MCP integration will automatically:
- Connect to the custom Jira MCP server
- Discover available tools
- Use MCP tools for Jira operations when available

### Testing MCP

```bash
# Test MCP configuration
python test_mcp_enabled.py

# Test full MCP integration
python test_mcp_integration_full.py

# Test Jira creation via MCP
python test_mcp_jira_creation.py
```

## 📚 RAG (Retrieval-Augmented Generation)

### Overview

The RAG service enhances responses by retrieving relevant context from your documents using vector embeddings.

### Features

- **Vector Store** - ChromaDB-based vector storage
- **Document Loading** - Support for PDF, TXT, and other formats
- **Embedding Generation** - OpenAI embeddings for semantic search
- **Caching** - Optional caching for improved performance
- **Context Retrieval** - Retrieves relevant context for user queries

### Usage

RAG is automatically used when:
- User asks questions that benefit from document context
- Documents are available in the `data/` directory
- RAG service is enabled in configuration

### Ingesting Documents

```bash
# Ingest PDF files
python ingest_pdf.py

# Documents are stored in data/ directory
```

## 🤖 LangGraph Agent

### Architecture

The chatbot uses LangGraph for agent orchestration:

```
User Input
    ↓
Intent Detection
    ↓
┌───────────────┬───────────────┬──────────────┐
│ General Chat  │ Jira Creation │ RAG Query    │
└───────────────┴───────────────┴──────────────┘
    ↓
Tool Execution (if needed)
    ↓
Response Generation
    ↓
User Response
```

### Intent Detection

The agent automatically detects user intents:
- **General Chat** - Conversational queries
- **Jira Creation** - Requests to create Jira issues
- **Information Query** - Questions that benefit from RAG

### Tool Usage

Tools are automatically selected based on intent:
- **MCP Tools** - Used when MCP is enabled and available
- **Custom Tools** - Fallback when MCP is unavailable
- **RAG Service** - Used for context-aware responses

## 🌐 Web UI

### Features

- **Modern Interface** - Clean, responsive design
- **Conversation Management** - Create, search, and manage conversations
- **Real-time Chat** - Instant messaging with AI
- **Message Actions** - Copy, regenerate responses
- **Conversation History** - Persistent conversation storage

### API Endpoints

- `POST /api/chat` - Send message and get AI response
- `GET /api/conversations` - Get all conversations
- `GET /api/conversations/<id>` - Get specific conversation
- `DELETE /api/conversations/<id>` - Delete conversation
- `POST /api/new-chat` - Create new conversation
- `PUT /api/conversations/<id>/title` - Update conversation title

## 📖 Documentation

> **📚 [Complete Documentation Index](docs/README.md)** - Browse all documentation organized by category

### Quick Links

**Getting Started:**
- **[docs/getting-started/QUICK_START.md](docs/getting-started/QUICK_START.md)** - Quick start guide for new users
- **[docs/getting-started/SETUP_ENV.md](docs/getting-started/SETUP_ENV.md)** - Environment setup instructions

**Core Features:**
- **[docs/features/agent/AGENT_FRAMEWORK.md](docs/features/agent/AGENT_FRAMEWORK.md)** - LangGraph agent framework
- **[docs/features/mcp/MCP_INTEGRATION_SUMMARY.md](docs/features/mcp/MCP_INTEGRATION_SUMMARY.md)** - MCP integration guide
- **[docs/features/rag/RAG_GUIDE.md](docs/features/rag/RAG_GUIDE.md)** - RAG service documentation
- **[docs/features/web-ui/WEB_UI_README.md](docs/features/web-ui/WEB_UI_README.md)** - Web UI documentation

**Architecture:**
- **[docs/architecture/FUTURE_ARCHITECTURE.md](docs/architecture/FUTURE_ARCHITECTURE.md)** - Future architecture plans
- **[docs/architecture/diagrams/architecture-diagram.drawio](docs/architecture/diagrams/architecture-diagram.drawio)** - Current architecture diagram
- **[docs/architecture/diagrams/architecture-diagram-future.drawio](docs/architecture/diagrams/architecture-diagram-future.drawio)** - Future architecture diagram

**Troubleshooting:**
- **[docs/troubleshooting/MCP_LOGGING_GUIDE.md](docs/troubleshooting/MCP_LOGGING_GUIDE.md)** - MCP logging and debugging
- **[docs/troubleshooting/WHY_ERROR_WASNT_CAUGHT.md](docs/troubleshooting/WHY_ERROR_WASNT_CAUGHT.md)** - Debugging guide

For a complete list of all documentation, see the **[Documentation Index](docs/README.md)**.

## 🧪 Testing

### Test Structure

Tests are organized in the `tests/` directory:

```
tests/
├── unit/              # Unit tests (isolated components)
├── integration/       # Integration tests (component interactions)
│   ├── mcp/          # MCP integration tests
│   ├── rag/          # RAG integration tests
│   ├── agent/        # Agent framework tests
│   ├── llm/          # LLM provider tests
│   └── memory/       # Memory system tests
├── e2e/              # End-to-end tests
└── fixtures/         # Test fixtures and utilities
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit          # Unit tests only
python run_tests.py --integration   # Integration tests only
python run_tests.py --e2e          # End-to-end tests only

# Run tests by feature
python run_tests.py --mcp          # MCP tests
python run_tests.py --rag          # RAG tests
python run_tests.py --agent        # Agent tests
python run_tests.py --llm          # LLM provider tests
python run_tests.py --memory       # Memory tests

# Using pytest directly
pytest tests/                       # Run all tests
pytest tests/unit/                 # Run unit tests
pytest tests/integration/mcp/      # Run MCP tests
pytest -v -m mcp                  # Run tests marked with 'mcp'
```

### Test Configuration

- **pytest.ini** - Pytest configuration with test markers
- **conftest.py** - Shared fixtures and test configuration
- **run_tests.py** - Convenient test runner script

# Test Jira creation
python test_mcp_jira_creation.py

# Test agent
python test_agent.py

# Test RAG
python test_rag.py
```

## 🔑 Getting API Keys

### OpenAI
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key to your `.env` file

### Google Gemini
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy the key to your `.env` file

### Jira API Token
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token to your `.env` file

## 🎨 Configuration Options

### LLM Provider Selection

Set `LLM_PROVIDER` in your `.env`:
- `openai` - OpenAI GPT models
- `gemini` - Google Gemini models
- `deepseek` - DeepSeek models

### MCP Configuration

- `USE_MCP=true` - Enable MCP integration
- MCP tools are automatically discovered and used

### RAG Configuration

- `RAG_ENABLE_CACHE=true` - Enable RAG caching
- `RAG_CACHE_TTL_HOURS=24` - Cache TTL in hours

### Coze Configuration

- `COZE_ENABLED=true` - Enable Coze platform integration
- `COZE_API_TOKEN` - Coze API token
- `COZE_BOT_ID` - Coze bot/agent ID
- `COZE_API_BASE_URL` - API base URL (`https://api.coze.cn` or `https://api.coze.com`)
- `COZE_API_TIMEOUT=300` - HTTP timeout in seconds for Coze API calls (default: 300)

## 🚨 Troubleshooting

### MCP Not Working
1. Check `USE_MCP=true` in `.env`
2. Verify Jira credentials are correct
3. Run `python test_mcp_enabled.py` to diagnose
4. Check logs for MCP initialization errors

### RAG Not Working
1. Ensure `OPENAI_API_KEY` is set (required for embeddings)
2. Check that documents exist in `data/` directory
3. Verify RAG service initialization in logs

### Agent Errors
1. Check LLM provider configuration
2. Verify API keys are valid
3. Review agent logs for specific errors

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Support

[Add support contact information here]

---

**Last Updated:** March 2026
