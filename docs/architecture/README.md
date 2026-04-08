# Architecture Documentation

This directory contains architecture diagrams and supporting documentation for the AI Requirement Tool system.

## Diagrams

### 1. Detailed Architecture Diagram
**File:** `architecture-diagram.mmd`

A comprehensive diagram showing the main layers and their relationships:
- Runtime and Web Layer (Flask app, runtime container, route blueprints)
- Chat Orchestration Layer (`src/chatbot.py`)
- Agent Orchestration Layer (`src/agent/agent_graph.py` and helper modules)
- Application Services Layer (requirement workflow, memory, evaluation, Coze)
- Integration Layer (MCP, direct tools, RAG, auth, optional gateway)
- LLM Layer (provider routing and fallback)
- External services and storage dependencies

### 2. Architecture Overview
**File:** `architecture-overview.mmd`

A high-level overview diagram showing:
- the current modular-monolith structure
- major components and boundaries
- data flow between runtime, chatbot, agent, services, and integrations

### 3. Request Flow Sequence Diagram
**File:** `request-flow-sequence.mmd`

A sequence diagram showing how a user request flows through the system:
- browser and API entrypoints
- runtime resolution and chatbot execution
- intent detection and routing
- execution paths for general chat, requirement workflow, RAG, and tool usage
- response generation and persistence

### 4. Intent Detection Decision Tree
**File:** `intent-detection-decision-tree.mmd`

A decision tree diagram showing the intent detection flow:
- keyword-based detection
- LLM-based detection for ambiguous cases
- confidence checks and fallback behavior

### 5. Project Structure Diagram
**File:** `project-structure-diagram.mmd`

A visual representation of the project folder structure:
- directory organization
- component grouping
- module dependency direction

## How to View Mermaid Diagrams

### Option 1: GitHub/GitLab
Mermaid diagrams are automatically rendered in markdown views on GitHub and GitLab. Open the `.mmd` files directly in the repository.

### Option 2: VS Code Extension
Install the "Markdown Preview Mermaid Support" extension in VS Code.

### Option 3: Online Mermaid Editor
1. Copy the content from any `.mmd` file
2. Paste it into [Mermaid Live Editor](https://mermaid.live/)
3. View and export the rendered diagram

### Option 4: Mermaid CLI
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Generate PNG from Mermaid file
mmdc -i architecture-diagram.mmd -o architecture-diagram.png
```

## Current Architecture Layers

The current codebase reflects the completed Phase 1 and Phase 2 refactors. It is best understood as a modular monolith with clearer runtime, orchestration, and service boundaries than the earlier design.

### 1. Runtime And Web Layer
- **Flask entry point:** `app.py`
- **Runtime container:** `src/webapp/runtime.py`
- **Route blueprints:** `src/webapp/routes/`
- **Web UI assets:** `web/templates/`, `web/static/`

This layer owns application startup, route registration, app-scoped dependency access, and browser/API entrypoints.

### 2. Chat Orchestration Layer
- **Main orchestrator:** `src/chatbot.py`

Responsibilities:
- initialize providers, memory, summarization, RAG, and tools
- manage top-level request execution
- invoke the LangGraph agent when enabled
- delegate the shared requirement workflow to the application service

### 3. Agent Orchestration Layer
- **Graph owner:** `src/agent/agent_graph.py`

After Phase 2, detailed agent behavior is split into focused helper modules:
- `intent_routing.py`
- `jira_nodes.py`
- `confluence_nodes.py`
- `rag_nodes.py`
- `coze_nodes.py`
- `general_chat_nodes.py`
- `requirement_workflow.py`
- `callbacks.py`

This keeps `agent_graph.py` centered on graph state and node orchestration instead of mixed business logic.

### 4. Application Services Layer
- `src/services/requirement_workflow_service.py`
- `src/services/intent_detector.py`
- `src/services/memory_manager.py`
- `src/services/memory_summarizer.py`
- `src/services/jira_maturity_evaluator.py`
- `src/services/coze_client.py`

This layer contains reusable workflow and business logic shared across execution paths.

### 5. Integration And Infrastructure Layer
- **MCP integration:** `src/mcp/`
- **Direct tools:** `src/tools/`
- **RAG pipeline:** `src/rag/`
- **Authentication:** `src/auth/`
- **Optional AI Gateway:** `src/gateway/`

This layer manages external service communication, provider plumbing, retrieval infrastructure, and protocol-specific adapters.

### 6. LLM Layer
- **Router:** `src/llm/router.py`
- **Providers:** OpenAI, Gemini, and DeepSeek implementations
- **Fallback behavior:** shared provider failover through the LLM infrastructure

### 7. Data And Storage Layer
- **Conversation storage:** SQLite-backed memory database
- **Vector storage:** ChromaDB
- **Configuration:** environment variables plus `config/config.py`
- **Document storage:** local files used for ingestion and retrieval

## Refactor Status

### Phase 1 Completed
- Shared requirement workflow logic extracted into `src/services/requirement_workflow_service.py`
- `Chatbot` delegated requirement workflow handling to the shared service

### Phase 2 Completed
- `src/agent/agent_graph.py` reduced to orchestration-centered responsibilities
- intent routing, Jira, Confluence, RAG, Coze, and general-chat execution moved into focused helper modules

### Phase 3 Planned
- ports, adapters, centralized composition, and stronger runtime/request boundaries are designed but not yet the default architecture
- see `../superpowers/specs/2026-04-05-phase-3-architecture-cleanup-design.md`

## Key Design Patterns

### 1. Agent-Based Architecture
The system uses LangGraph to:
- detect intent
- route requests
- orchestrate tools and services
- manage conversational execution state

### 2. Shared Application Service
`RequirementWorkflowService` centralizes:
- backlog generation
- Jira issue creation
- maturity evaluation
- Confluence content assembly
- user-facing workflow response formatting

This removes duplicated workflow logic from the chatbot and agent layers.

### 3. Multi-Provider LLM Support
- router pattern for provider selection
- automatic fallback to backup providers
- consistent interface across providers

### 4. Lazy Tool Loading
- tools initialize only when needed
- reduces startup overhead
- helps avoid unnecessary dependency work during boot

### 5. Runtime Container Pattern
`AppRuntime` centralizes app-scoped dependency ownership for Flask handlers and reduces reliance on module-level globals.

### 6. MCP Integration
- Model Context Protocol for standardized tool integration
- direct-tool fallback when MCP is unavailable
- integration helpers compatible with the current agent flow

### 7. RAG Pipeline
- document ingestion and loading
- chunking and embedding generation
- semantic retrieval
- prompt augmentation for grounded responses

## Data Flow

1. **User Request** -> Web UI or API -> Flask route blueprint -> `AppRuntime`
2. **Runtime** -> `Chatbot`
3. **Chatbot** -> LangGraph agent or direct provider flow
4. **Agent** -> intent routing -> general chat, requirement workflow, RAG, Coze, or tool path
5. **Handler/Workflow** -> shared services, RAG, MCP, direct tools, or LLM providers
6. **Response** -> memory persistence -> Flask response -> Web UI

## Common Request Paths

### Standard Chat
- Browser -> Flask route -> runtime -> `Chatbot` -> provider or agent -> response

### Requirement Workflow
- User request -> intent detection -> backlog generation -> Jira creation -> optional maturity evaluation -> optional Confluence page creation -> formatted response

### RAG Query
- User request -> intent detection -> retrieval -> prompt augmentation -> LLM response

## Future Architecture

The next planned architecture step is Phase 3 cleanup, not a wholesale replacement of the current modular-monolith design.

See:
- `../superpowers/specs/2026-04-05-phase-3-architecture-cleanup-design.md`
- `FUTURE_ARCHITECTURE.md`

Phase 3 focuses on:
- application-facing ports for Jira, Confluence, evaluation, and RAG ingestion
- adapters that hide MCP-vs-direct fallback policy
- centralized composition and runtime wiring
- clearer app-scoped versus request-scoped ownership
- improved execution safety and testability

## Documentation

### Project Structure And Design
**File:** `../PROJECT_STRUCTURE_AND_DESIGN.md`

Comprehensive overview of:
- project folder structure
- architecture layers and design decisions
- component interactions and data flow
- testing and deployment considerations

### Requirement Workflow Refactor Design
**File:** `../superpowers/specs/2026-04-03-requirement-workflow-refactor-design.md`

Phase 1 and Phase 2 architecture refactor notes:
- workflow-service extraction
- agent helper-module extraction
- implementation rationale and verification summary

### Phase 3 Cleanup Design
**File:** `../superpowers/specs/2026-04-05-phase-3-architecture-cleanup-design.md`

Planned cleanup topics:
- ports and adapters
- runtime/composition cleanup
- request-safety improvements
- incremental migration direction

### Future Architecture
**File:** `FUTURE_ARCHITECTURE.md`

Longer-range ideas beyond the current Phase 3 cleanup scope.

## Related Documentation

- [Agent Framework Documentation](../features/agent/AGENT_FRAMEWORK.md)
- [MCP Integration Guide](../features/mcp/MCP_INTEGRATION_SUMMARY.md)
- [RAG Service Guide](../features/rag/RAG_GUIDE.md)
- [Web UI Documentation](../features/web-ui/WEB_UI_README.md)
- [Requirement Workflow Refactor Design](../superpowers/specs/2026-04-03-requirement-workflow-refactor-design.md)
- [Phase 3 Architecture Cleanup Design](../superpowers/specs/2026-04-05-phase-3-architecture-cleanup-design.md)
