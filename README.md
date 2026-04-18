# Enterprise GenAI Assistant

An enterprise-oriented GenAI assistant combining conversational AI, document Q&A (RAG), and Jira/Confluence workflows via MCP and APIs with multi-provider LLM routing, an optional centralized gateway for caching and rate-limiting, a responsive web UI, and production-grade observability.

Built for teams that need more than a generic chatbot: structured intent detection routes requests to the right tool automatically, RAG grounds answers in your internal knowledge base, and MCP bridges the assistant directly into your Atlassian toolchain.

## Key Features

### Latest Change Highlights (2026-04-13)

- Product agent flow redesigned for clearer end-to-end user progression
- Internal orchestration refactored to improve maintainability and extension safety
- UX behavior improved across chat validation, error handling, and workflow response consistency
- Final polish package added:
 - `docs/release/2026-04-13-final-polish/QA_SIGNOFF_CHECKLIST.md`
 - `docs/release/2026-04-13-final-polish/METRICS_INSTRUMENTATION_REVIEW.md`
 - `docs/release/2026-04-13-final-polish/RELEASE_NOTES_DRAFT.md`

### Conversational AI
- **LangGraph Agent Framework** - Stateful agent graph with intent detection and multi-step tool orchestration
- **Refactored Agent Orchestration** - `src/agent/agent_graph.py` now focuses on orchestration while intent routing, Jira, Confluence, RAG, Coze, and general chat behavior live in focused helper modules
- **Requirement SDLC Agent Mode** - Staged BA-guided requirement drafting with explicit approval before durable Jira/Confluence/RAG lifecycle execution
- **Conversation Memory** - Persistent history with automatic summarization to stay within context limits
- **Intent Routing** - Automatically distinguishes general chat, document Q&A, and Jira/Confluence actions
- **Coze Platform Integration** - ByteDance Coze agent support via cozepy SDK with configurable HTTP timeout

### Document Q&A (RAG)
- **RAG Service** - Retrieval-Augmented Generation over internal documents with vector embeddings
- **Vector Store & Caching** - Fast similarity search with a TTL-based RAG cache to reduce redundant embedding calls
- **Document Loader** - Ingest documents from local storage or connected sources

### Jira & Confluence Workflows
- **Shared Requirement Workflow Service** - Centralized requirement backlog generation, Jira creation, maturity evaluation, and Confluence-page assembly in `src/services/requirement_workflow_service.py`
- **MCP Integration** - Model Context Protocol server for Jira and Confluence, enabling natural-language issue creation, search, and page management
- **Custom Tools** - Direct REST API tools for Jira issue management and Confluence content operations
- **Jira Maturity Evaluator** - Automated assessment of issue quality and completeness

### Multi-Provider LLM Routing
- **Provider Support** - OpenAI, Google Gemini, and DeepSeek with a unified interface
- **Automatic Fallback** - Transparent failover across providers on errors or rate limits
- **Optional Centralized Gateway** - Layer in a gateway for shared caching, rate-limit enforcement, and cost visibility across teams

### Web UI & Observability
- **Modern Web UI** - Responsive chat interface served by Flask, no build step required
- **Prometheus Metrics** - HTTP request counters, latency histograms, and LLM token/cost metrics via `/metrics`
- **Grafana Dashboards** - Pre-built dashboards for request rate, error rate, and LLM usage
- **Structured Logging** - Request-level logs for debugging and audit trails

### Production Readiness
- **GKE Deployment** - Kubernetes manifests with LoadBalancer service and Recreate rollout strategy
- **CI/CD via GitHub Actions** - Automated test, build, push, and deploy pipeline
- **Lazy Tool Loading** - Tools initialized on demand to minimize startup overhead
- **Error Recovery** - Automatic fallback mechanisms at agent and provider level
- **Integration & E2E Tests** - Full test suite covering MCP, RAG, agent, LLM providers, memory, API routes, and gateway components

## Project Structure

```text
AI_Requirement_Tool/
|-- app.py # Flask web server entrypoint
|-- config/
| `-- config.py # Centralized configuration
|-- src/
| |-- chatbot.py # Main chatbot orchestrator used by Flask
| |-- agent/ # LangGraph orchestration and node helpers
| | |-- agent_graph.py # Graph assembly and state orchestration
| | |-- intent_routing.py # Intent routing helpers
| | |-- jira_nodes.py # Jira execution helpers
| | |-- confluence_nodes.py # Confluence execution helpers
| | |-- rag_nodes.py # RAG node helpers
| | |-- coze_nodes.py # Coze node helpers
| | |-- general_chat_nodes.py # General chat helpers
| | |-- requirement_workflow.py
| | `-- callbacks.py
| |-- services/ # Application services
| | |-- requirement_workflow_service.py
| | |-- requirement_sdlc_agent_service.py
| | |-- intent_detector.py
| | |-- jira_maturity_evaluator.py
| | |-- memory_manager.py
| | |-- memory_summarizer.py
| | `-- coze_client.py
| |-- application/ # Phase 3 application ports and contracts
| | `-- ports/
| |-- adapters/ # Fallback/direct adapters behind ports
| | |-- jira/
| | |-- confluence/
| | `-- evaluation/
| |-- runtime/ # Centralized dependency composition
| | `-- composition.py
| |-- webapp/ # Flask runtime container and route blueprints
| | |-- runtime.py
| | `-- routes/
| |-- auth/ # Authentication services and middleware
| |-- llm/ # Multi-provider LLM infrastructure
| |-- mcp/ # MCP client and integration logic
| |-- rag/ # RAG pipeline
| |-- tools/ # Direct Jira and Confluence tools
| |-- gateway/ # Optional FastAPI AI Gateway
| |-- models/
| `-- utils/
|-- web/ # Web UI frontend
| |-- templates/
| `-- static/
|-- tests/
| |-- unit/
| |-- integration/
| `-- e2e/
|-- docs/
| |-- architecture/
| |-- features/
| `-- superpowers/
|-- requirements.txt
|-- pytest.ini
|-- run_tests.py
`-- README.md
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AI_Requirement_Tool
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root or set environment variables:

```bash
# LLM Provider Configuration
LLM_PROVIDER=openai # Options: 'openai', 'gemini', 'deepseek'
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
USE_MCP=true # Enable MCP integration

# RAG Configuration (optional)
RAG_ENABLE_CACHE=true
RAG_CACHE_TTL_HOURS=24
```

See [docs/getting-started/SETUP_ENV.md](docs/getting-started/SETUP_ENV.md) for environment setup examples across operating systems.

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

**Optional AI Gateway:**
```bash
uvicorn src.gateway.gateway_service:create_gateway_app --factory --reload --port 8001
```

## Usage Examples

### General Chat
```
You: What is Python##
Chatbot: Python is a high-level programming language...
```

### Create Jira Issue
```
You: Create a new Jira issue about "Add Redis cache for RAG service"
Chatbot: I'll create a Jira issue for you...
 Created issue SCRUM-123 via MCP tool
Link: https://yourcompany.atlassian.net/browse/SCRUM-123
```

### Intent Detection
The agent automatically detects user intents:
- **General Chat** - Regular conversation
- **Jira Creation** - Creating Jira issues
- **Question Answering** - Using RAG for context-aware responses

## MCP Integration

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
pytest tests/integration/mcp/test_mcp_enabled.py -v

# Test full MCP integration
pytest tests/integration/mcp/test_mcp_integration_full.py -v

# Test Jira creation via MCP
pytest tests/integration/mcp/test_mcp_jira_creation.py -v
```

## RAG (Retrieval-Augmented Generation)

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

## LangGraph Agent

### Current Architecture

The chatbot uses LangGraph for orchestration, but the architecture has been refactored so responsibilities are split across smaller modules.

```text
User
  |
  v
Chatbot
  |
  v
ChatbotAgent / LangGraph
  |
  v
intent_detection
  |
  +--> requirement_sdlc_agent
  |      Purpose: staged BA-guided requirement drafting and approval flow
  |      Impl: src/services/requirement_sdlc_agent_service.py
  |
  +--> confluence_creation
  |      Purpose: direct freeform Confluence or wiki page creation
  |      Impl: src/services/confluence_creation_service.py
  |
  +--> general_chat
  |      Purpose: normal conversation / fallback path
  |
  +--> rag_query
  |      Purpose: document Q&A / knowledge retrieval
  |
  +--> coze_agent
  |      Purpose: handoff to Coze when configured
  |
  +--> jira_creation
         Purpose: create Jira issue
         |
         v
      evaluation
         |
         +--> confluence_creation
         |      Purpose: create Confluence page after evaluation
         |
         +--> end
```

### Refactor Status

- **Phase 1 completed** - Shared requirement workflow logic was extracted into `src/services/requirement_workflow_service.py`
- **Phase 2 completed** - `src/agent/agent_graph.py` now delegates to focused helper modules for intent routing, Jira, Confluence, RAG, Coze, and general chat
- **Phase 3 foundations implemented (ongoing cleanup)** - Ports/adapters and centralized composition are present in `src/application`, `src/adapters`, and `src/runtime`; runtime and request-safety hardening continues incrementally

### Intent Detection

The agent automatically detects user intents:
- **General Chat** - Conversational queries
- **Jira Creation** - Requests to create Jira issues
- **Confluence Creation** - Requests to create a Confluence page directly from freeform notes
- **Information Query** - Questions that benefit from RAG
- **Coze Agent** - Requests routed to the Coze integration when enabled
- **Requirement SDLC Agent** - Requests to draft, revise, confirm, or execute requirement lifecycle work

### Tool Usage

Tools are automatically selected based on intent:
- **Requirement Workflow Service** - Used for shared backlog generation, Jira creation, maturity evaluation, and Confluence content assembly
- **MCP Tools** - Used when MCP is enabled and available
- **Custom Tools** - Fallback when MCP is unavailable
- **RAG Service** - Used for context-aware responses

## Web UI

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

## Documentation

> ** [Complete Documentation Index](docs/README.md)** - Browse all documentation organized by category

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
- **[docs/architecture/README.md](docs/architecture/README.md)** - Current architecture documentation
- **[docs/architecture/post-migration-hardening-checklist.md](docs/architecture/post-migration-hardening-checklist.md)** - Post-migration hardening and release-readiness checklist
- **[docs/superpowers/specs/2026-04-03-requirement-workflow-refactor-design.md](docs/superpowers/specs/2026-04-03-requirement-workflow-refactor-design.md)** - Phase 1 and Phase 2 refactor design and completion notes
- **[docs/superpowers/specs/2026-04-05-phase-3-architecture-cleanup-design.md](docs/superpowers/specs/2026-04-05-phase-3-architecture-cleanup-design.md)** - Phase 3 architecture cleanup design and migration direction
- **[docs/architecture/diagrams/architecture-diagram.drawio](docs/architecture/diagrams/architecture-diagram.drawio)** - Current architecture diagram
- **[docs/architecture/diagrams/architecture-diagram-future.drawio](docs/architecture/diagrams/architecture-diagram-future.drawio)** - Future architecture diagram

**Troubleshooting:**
- **[docs/troubleshooting/MCP_LOGGING_GUIDE.md](docs/troubleshooting/MCP_LOGGING_GUIDE.md)** - MCP logging and debugging
- **[docs/troubleshooting/WHY_ERROR_WASNT_CAUGHT.md](docs/troubleshooting/WHY_ERROR_WASNT_CAUGHT.md)** - Debugging guide

For a complete list of all documentation, see the **[Documentation Index](docs/README.md)**.

## Testing

### Test Structure

Tests are organized in the `tests/` directory:
- `tests/unit/` - Unit tests (isolated components)
- `tests/integration/` - Integration tests (component interactions)
- `tests/integration/mcp/` - MCP integration tests
- `tests/integration/rag/` - RAG integration tests
- `tests/integration/agent/` - Agent integration tests
- `tests/integration/llm/` - LLM provider tests
- `tests/integration/memory/` - Memory integration tests
- `tests/e2e/` - End-to-end UI and full-stack tests
- `tests/fixtures/` - Shared test helpers and fixture data

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit # Unit tests only
python run_tests.py --integration # Integration tests only
python run_tests.py --e2e # End-to-end tests only

# Run tests by feature
python run_tests.py --mcp # MCP tests
python run_tests.py --rag # RAG tests
python run_tests.py --agent # Agent tests
python run_tests.py --llm # LLM provider tests
python run_tests.py --memory # Memory tests

# Using pytest directly
pytest tests/ # Run all tests
pytest tests/unit/ # Run unit tests
pytest tests/integration/mcp/ # Run MCP tests
pytest -v -m mcp # Run tests marked with 'mcp'
```

### Test Configuration

- **pytest.ini** - Pytest configuration with test markers
- **conftest.py** - Shared fixtures and test configuration
- **run_tests.py** - Convenient test runner script

```bash
# Focused integration runs
pytest tests/integration/mcp/test_mcp_jira_creation.py -v
pytest tests/integration/agent/ -v -m agent
pytest tests/integration/rag/ -v -m rag
```

## Getting API Keys

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

## Configuration Options

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

## CI/CD Pipeline

The project uses GitHub Actions for automated build, test, and deployment to Google Kubernetes Engine (GKE).

### Workflows

| Workflow | File | Trigger |
|---|---|---|
| CI Build, Test & Push | `.github/workflows/ci.yml` | Push or PR to `main` |
| CD Deploy to GKE | `.github/workflows/cd.yml` | CI workflow completes successfully |

### CI Pipeline (`ci.yml`)

1. **Checkout** source code
2. **Set up Python 3.11** with pip caching
3. **Run unit tests** via `pytest tests/unit/`
4. *(On push to `main` only)*
5. **Authenticate to GCP** using `GCP_SA_KEY` service account key
6. **Configure Docker** for Artifact Registry
7. **Build Docker image** tagged with commit SHA and `latest`
8. **Push image** to `us-central1-docker.pkg.dev/{GCP_PROJECT_ID}/ai-requirement-tool/ai-requirement-tool`

### CD Pipeline (`cd.yml`)

1. **Authenticate to GCP**
2. **Get GKE credentials** for cluster `helloworld-cluster` in `us-central1`
3. **Inject image** (commit SHA tag) into `k8s/deployment.yaml`
4. **Apply** `k8s/deployment.yaml` and `k8s/service.yaml`
5. **Wait for rollout** (`kubectl rollout status deployment/ai-tool`)
6. **Print external IP** of the LoadBalancer service

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `GCP_SA_KEY` | GCP service account key JSON (roles: `artifactregistry.writer`, `container.developer`) |
| `GCP_PROJECT_ID` | GCP project ID |

> **Security note:** The pipeline currently uses a long-lived service account key (`GCP_SA_KEY`). Migrating to [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation) is recommended before production use.

### Infrastructure

- **Registry:** `us-central1-docker.pkg.dev/{GCP_PROJECT_ID}/ai-requirement-tool/ai-requirement-tool`
- **Cluster:** `helloworld-cluster` (us-central1)
- **Deployment:** `ai-tool` (1 replica)
- **Service:** `ai-tool-service` (LoadBalancer)
- **Endpoint discovery:** CD workflow prints the current external IP after deployment
- **Health check pattern:** `http://<external-ip>/api/health`

> The GKE LoadBalancer IP is dynamic. Use the CD workflow output or `kubectl get svc ai-tool-service` to retrieve the current endpoint.

---

## Troubleshooting

### MCP Not Working
1. Check `USE_MCP=true` in `.env`
2. Verify Jira credentials are correct
3. Run `pytest tests/integration/mcp/test_mcp_enabled.py -v` to diagnose
4. Check logs for MCP initialization errors

### RAG Not Working
1. Ensure `OPENAI_API_KEY` is set (required for embeddings)
2. Check that documents exist in `data/` directory
3. Verify RAG service initialization in logs

### Agent Errors
1. Check LLM provider configuration
2. Verify API keys are valid
3. Review agent logs for specific errors

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Support

[Add support contact information here]

---

**Last Updated:** April 2026
