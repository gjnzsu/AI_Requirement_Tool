# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Requirement Tool** is an enterprise GenAI assistant combining conversational AI, document Q&A (RAG), and Jira/Confluence workflows via MCP and APIs with multi-provider LLM routing, an optional centralized gateway for caching and rate-limiting, a responsive web UI, and production-grade observability.

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Set required env vars (copy .env.example to .env and configure)
# Start the web server
python app.py
```

The server runs on port `5000` by default (configurable via environment variables).

## Environment Variables (`.env`)

### Core Configuration
| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | LLM provider: `openai`, `gemini`, `deepseek` |
| `OPENAI_API_KEY` | *(required)* | OpenAI API key |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | OpenAI model name |
| `GEMINI_API_KEY` | - | Google Gemini API key |
| `DEEPSEEK_API_KEY` | - | DeepSeek API key |

### Jira & Confluence
| Variable | Default | Description |
|---|---|---|
| `JIRA_URL` | - | Atlassian Jira URL |
| `JIRA_EMAIL` | - | Jira user email |
| `JIRA_API_TOKEN` | - | Jira API token |
| `JIRA_PROJECT_KEY` | - | Default Jira project key |
| `CONFLUENCE_URL` | - | Confluence wiki URL |
| `CONFLUENCE_SPACE_KEY` | - | Default Confluence space |

### MCP & Tools
| Variable | Default | Description |
|---|---|---|
| `USE_MCP` | `true` | Enable MCP protocol for Jira/Confluence |
| `ENABLE_MCP_TOOLS` | `true` | Enable MCP tools integration |
| `LAZY_LOAD_TOOLS` | `true` | Initialize tools on demand |

### RAG Configuration
| Variable | Default | Description |
|---|---|---|
| `USE_RAG` | `true` | Enable RAG for document Q&A |
| `RAG_ENABLE_CACHE` | `true` | Enable RAG result caching |
| `RAG_CACHE_TTL_HOURS` | `24` | Cache TTL in hours |
| `RAG_TOP_K` | `3` | Number of chunks to retrieve |

### Coze Platform
| Variable | Default | Description |
|---|---|---|
| `COZE_ENABLED` | `false` | Enable Coze platform integration |
| `COZE_API_TOKEN` | - | Coze API token |
| `COZE_BOT_ID` | - | Coze bot/agent ID |
| `ASYNC_COZE_ENABLED` | `true` | Use async execution for Coze |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for Celery broker |

### Authentication
| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | - | JWT secret (change in production) |
| `JWT_EXPIRATION_HOURS` | `24` | JWT token expiration |

### AI Gateway (Optional)
| Variable | Default | Description |
|---|---|---|
| `GATEWAY_ENABLED` | `false` | Enable centralized AI gateway |
| `USE_GATEWAY` | `false` | Route LLM calls through gateway |
| `GATEWAY_CACHE_ENABLED` | `true` | Enable gateway caching |

## Architecture

### High-Level Overview

The AI Requirement Tool is built as a layered architecture with clear separation of concerns:

1. **User Layer**: Web UI (browser) and API clients
2. **Web Layer**: Flask app with REST API routes (auth, core, conversations, jobs)
3. **Core Services**: Chatbot orchestrator, LangGraph agent, memory manager, authentication
4. **Agent Execution**: Sync paths (chat, RAG, Jira, Confluence) and async path (Coze via Celery)
5. **Integration Layer**: Multi-provider LLM routing, optional AI gateway, MCP integration, direct tools
6. **Data Layer**: RAG service, memory DB (SQLite), Redis (Celery broker)
7. **External Systems**: Atlassian (Jira/Confluence), Coze platform
8. **Observability**: Prometheus metrics, Grafana dashboards

### Main Request Flow

![Main Request Flow](docs/architecture/diagrams/main-request-flow.drawio.png)

This flowchart shows how a user request flows through the system:
1. User sends message → Authentication check
2. Intent detection by LangGraph agent
3. Route to appropriate execution path (6 different intents)
4. For Coze: decision between sync or async execution
5. Response formatted and returned to user

Source: [main-request-flow.drawio](docs/architecture/diagrams/main-request-flow.drawio)

### Architecture Diagram

![AI Requirement Tool Architecture](docs/architecture/diagrams/ai-requirement-tool-architecture-comprehensive.drawio.png)

Source: [ai-requirement-tool-architecture-comprehensive.drawio](docs/architecture/diagrams/ai-requirement-tool-architecture-comprehensive.drawio)

### Key Components

#### Flask Web Application (`app.py`)
- Main entry point serving REST API and web UI
- Routes organized in blueprints: `auth`, `core`, `conversations`, `jobs`
- Prometheus metrics instrumentation on all endpoints
- JWT-based authentication middleware
- CORS enabled for API access

#### Chatbot Orchestrator (`src/chatbot.py`)
- Main chatbot class coordinating all services
- Manages LLM provider selection and fallback
- Integrates with LangGraph agent for intelligent routing
- Handles conversation context and memory
- Token usage tracking for cost monitoring

#### LangGraph Agent (`src/agent/agent_graph.py`)
- Stateful agent graph with intent detection
- Routes requests to appropriate execution paths:
  - `general_chat`: Normal conversation
  - `rag_query`: Document Q&A using RAG
  - `jira_creation`: Create Jira issues
  - `confluence_creation`: Create Confluence pages
  - `requirement_sdlc_agent`: Guided requirement workflow
  - `coze_agent`: Handoff to Coze platform (async)
- Node helpers in focused modules: `intent_routing.py`, `jira_nodes.py`, `confluence_nodes.py`, `rag_nodes.py`, `coze_nodes.py`, `general_chat_nodes.py`

#### Multi-Provider LLM (`src/llm/`)
- Unified interface for OpenAI, Gemini, DeepSeek
- `LLMRouter`: Automatic provider selection and fallback
- `LLMProviderManager`: Provider lifecycle management
- Cost tracking per provider/model
- Optional AI Gateway integration for caching and rate limiting

#### MCP Integration (`src/mcp/`)
- Model Context Protocol client for Atlassian tools
- Automatic tool discovery and wrapping
- Fallback to direct REST API tools when MCP unavailable
- Lazy initialization for faster startup

#### RAG Service (`src/rag/`)
- Vector store (ChromaDB) for document embeddings
- Document loader supporting PDF, TXT, and other formats
- Embedding generation via OpenAI
- Query cache with configurable TTL
- Text chunking with overlap for better context

#### Memory Manager (`src/services/memory_manager.py`)
- Persistent conversation storage (SQLite)
- Automatic context summarization when approaching limits
- Conversation title generation
- Message history management

#### Async Execution (`src/async_jobs/`)
- Celery worker for long-running Coze requests
- Redis as broker and result backend
- Job status polling via `/api/jobs/<job_id>`
- Prevents web request timeout on slow operations

### API Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

#### Chat
- `POST /api/chat` - Send message and get AI response
  - Body: `{ message, conversation_id?, model?, agent_mode? }`
  - Returns: `{ response, conversation_id, agent_mode, ui_actions, workflow_progress }`
  - Returns 202 for async Coze jobs with `{ job_id, status }`

#### Conversations
- `GET /api/conversations` - List all conversations
- `GET /api/conversations/<id>` - Get conversation details
- `DELETE /api/conversations/<id>` - Delete conversation
- `POST /api/new-chat` - Create new conversation
- `PUT /api/conversations/<id>/title` - Update conversation title

#### Jobs (Async)
- `GET /api/jobs/<job_id>` - Poll async job status
  - Returns: `{ job_id, status, result?, error? }`
  - Status: `queued`, `running`, `completed`, `failed`

#### Models
- `GET /api/current-model` - Get current LLM provider and available models

#### Health & Metrics
- `GET /api/health` - Health check endpoint
- `GET /metrics` - Prometheus metrics endpoint

### Project Structure

```
AI_Requirement_Tool/
├── app.py                          # Flask web server entrypoint
├── config/
│   └── config.py                   # Centralized configuration
├── src/
│   ├── chatbot.py                  # Main chatbot orchestrator
│   ├── agent/                      # LangGraph agent and nodes
│   │   ├── agent_graph.py          # Graph assembly
│   │   ├── intent_routing.py       # Intent detection helpers
│   │   ├── jira_nodes.py           # Jira execution
│   │   ├── confluence_nodes.py     # Confluence execution
│   │   ├── rag_nodes.py            # RAG nodes
│   │   ├── coze_nodes.py           # Coze integration
│   │   └── general_chat_nodes.py   # General chat
│   ├── services/                   # Application services
│   │   ├── requirement_workflow_service.py
│   │   ├── requirement_sdlc_agent_service.py
│   │   ├── confluence_creation_service.py
│   │   ├── memory_manager.py
│   │   ├── coze_client.py
│   │   └── jira_maturity_evaluator.py
│   ├── llm/                        # Multi-provider LLM
│   │   ├── router.py               # LLM routing and fallback
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   └── deepseek_provider.py
│   ├── mcp/                        # MCP integration
│   │   ├── mcp_client.py
│   │   └── mcp_integration.py
│   ├── rag/                        # RAG pipeline
│   │   ├── rag_service.py
│   │   ├── vector_store.py
│   │   └── document_loader.py
│   ├── tools/                      # Direct API tools
│   │   ├── jira_tool.py
│   │   └── confluence_tool.py
│   ├── gateway/                    # Optional AI Gateway
│   ├── auth/                       # Authentication
│   ├── webapp/                     # Flask runtime and routes
│   ├── async_jobs/                 # Celery tasks
│   ├── application/                # Ports and contracts
│   ├── adapters/                   # Fallback adapters
│   └── runtime/                    # Dependency composition
├── web/                            # Web UI frontend
│   ├── templates/
│   └── static/
├── k8s/                            # Kubernetes manifests
├── tests/                          # Test suite
└── docs/                           # Documentation
```

## Post-Deployment Log & Test Checks

When asked to **"triage logs"**, **"check test status"**, **"post deployment check"**, or **"verify deployment"**, run the following checks in order and return a structured report.

### Stack Context
- Deployments: `ai-tool`, `grafana`, `prometheus`
- App service: `ai-tool-service` (LoadBalancer, port 80 → pod 5000), external IP `34.133.164.110`
- Grafana: external IP `136.114.77.0` (port 80)
- Prometheus: internal `prometheus-service:9090`

### Checklist

1. **Pod & Deployment Health**
   ```bash
   kubectl get pods
   kubectl get deployments
   ```
   Flag any pod not `1/1 Running` or with non-zero restarts.

2. **Application Logs** — scan for errors
   ```bash
   kubectl logs -l app=ai-tool --tail=50
   ```
   Search for: `ERROR`, `Exception`, `Traceback`, `CRITICAL`, `500`. Report exact line and timestamp.

3. **Prometheus Scrape Health**
   ```bash
   kubectl exec deploy/prometheus -- wget -qO- http://localhost:9090/api/v1/targets
   ```
   Confirm `health: "up"` for `ai-tool` target. Report `lastError` if down.

4. **Live Metric Verification**
   ```bash
   kubectl exec deploy/prometheus -- wget -qO- 'http://localhost:9090/api/v1/query?query=rate(http_requests_total[2m])'
   ```
   Confirm non-empty result. Report current request rate per endpoint.

5. **Grafana Provisioning**
   ```bash
   kubectl logs -l app=grafana --tail=30
   ```
   Confirm `"provisioned dashboard is up to date"` for `ai-tool.json`. Flag any `level=error`.

6. **Culprit Commit Analysis** (only if errors found in steps 2–5)
   ```bash
   git log --oneline -10
   ```
   Cross-reference error timestamps against recent commits.

### Report Format
```
## Post-Deployment Health Report
**Pods**: [OK / ISSUES: <details>]
**App Logs**: [Clean / ERRORS: <file:line> <message>]
**Prometheus Scrape**: [UP / DOWN: <lastError>]
**Live Metrics**: [Data present / No data: <reason>]
**Grafana**: [OK / ISSUES: <details>]
**Culprit Commit** (if errors): [hash] - <message>
**Verdict**: HEALTHY / NEEDS ATTENTION
```
If all green, a one-liner "All systems healthy" is sufficient.
