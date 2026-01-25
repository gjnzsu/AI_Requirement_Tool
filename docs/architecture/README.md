# Architecture Documentation

This directory contains architecture diagrams and documentation for the Generative AI Chatbot system.

## Diagrams

### 1. Detailed Architecture Diagram
**File:** `architecture-diagram.mmd`

A comprehensive diagram showing all components, layers, and their relationships:
- User Interface Layer (Web UI, REST API)
- Application Layer (Flask App, Chatbot)
- Agent Layer (LangGraph Agent, Intent Detection, Router)
- Service Layer (RAG, Memory, MCP Integration)
- Tool Layer (Jira, Confluence Tools)
- LLM Layer (Multi-provider routing)
- RAG Components (Document processing pipeline)
- External Services (APIs and MCP servers)
- Data Storage (Databases and configuration)

### 2. Architecture Overview
**File:** `architecture-overview.mmd`

A high-level overview diagram showing the main layers and data flow:
- Simplified view of the system architecture
- Key components and their relationships
- Data flow between layers

### 3. Request Flow Sequence Diagram
**File:** `request-flow-sequence.mmd`

A sequence diagram showing how a user request flows through the system:
- User interaction flow
- Intent detection and routing
- Different execution paths (General Chat, RAG Query, Tool Execution)
- Response generation and storage

### 4. Intent Detection Decision Tree
**File:** `intent-detection-decision-tree.mmd`

A decision tree diagram showing the complete intent detection flow:
- Keyword-based detection (fast path)
- LLM-based detection (ambiguous cases)
- Cache checking and confidence validation
- Fallback mechanisms

### 5. Project Structure Diagram
**File:** `project-structure-diagram.mmd`

A visual representation of the project folder structure:
- Directory organization
- Component relationships
- Module dependencies

## How to View Mermaid Diagrams

### Option 1: GitHub/GitLab
Mermaid diagrams are automatically rendered in markdown files on GitHub and GitLab. Simply view the `.mmd` files in the repository.

### Option 2: VS Code Extension
Install the "Markdown Preview Mermaid Support" extension in VS Code to preview diagrams.

### Option 3: Online Mermaid Editor
1. Copy the content from any `.mmd` file
2. Paste it into [Mermaid Live Editor](https://mermaid.live/)
3. View and export the diagram

### Option 4: Mermaid CLI
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Generate PNG from Mermaid file
mmdc -i architecture-diagram.mmd -o architecture-diagram.png
```

## Architecture Layers

### 1. User Interface Layer
- **Web UI**: Flask-based web interface with HTML/CSS/JavaScript
- **REST API**: Flask routes for chat, conversations, and management

### 2. Application Layer
- **Flask Application**: Main web server (`app.py`)
- **Chatbot Class**: Core chatbot logic (`chatbot.py`)

### 3. Agent Layer
- **LangGraph Agent**: Intelligent agent framework (`agent_graph.py`)
- **Intent Detection**: Classifies user intents (general_chat, jira_creation, rag_query, confluence_creation)
- **Router**: Routes requests to appropriate handlers based on intent

### 4. Service Layer
- **RAG Service**: Retrieval-Augmented Generation for context-aware responses
- **Memory Manager**: Persistent conversation storage and retrieval
- **Memory Summarizer**: Summarizes long conversations to manage context window
- **MCP Integration**: Model Context Protocol integration for external tools
- **Jira Maturity Evaluator**: Evaluates Jira requirement maturity scores

### 5. Tool Layer
- **Jira Tool**: Custom Jira integration tool
- **Confluence Tool**: Custom Confluence integration tool
- **MCP Tool Wrappers**: LangChain-compatible wrappers for MCP tools

### 6. LLM Layer
- **LLM Router**: Routes requests to appropriate LLM provider
- **OpenAI Provider**: OpenAI GPT models integration
- **Gemini Provider**: Google Gemini models integration
- **DeepSeek Provider**: DeepSeek models integration

### 7. RAG Components
- **Document Loader**: Loads documents from various formats (PDF, TXT)
- **Text Chunker**: Splits documents into chunks for embedding
- **Embedding Generator**: Generates vector embeddings using OpenAI
- **Vector Store**: ChromaDB-based vector storage
- **RAG Cache**: Caches RAG query results

### 8. External Services
- **LLM APIs**: OpenAI, Google Gemini, DeepSeek APIs
- **Atlassian APIs**: Jira and Confluence REST APIs
- **MCP Server**: Custom MCP server for Jira/Confluence operations

### 9. Data Storage
- **Memory Database**: SQLite database for conversation storage
- **Vector Database**: ChromaDB for document embeddings
- **Configuration**: Environment variables and config files
- **Document Storage**: File system storage for documents

## Key Design Patterns

### 1. Agent-Based Architecture
The system uses LangGraph to create an intelligent agent that:
- Detects user intent automatically
- Routes requests to appropriate handlers
- Orchestrates multiple tools and services
- Manages conversation state

### 2. Multi-Provider LLM Support
- Router pattern for LLM provider selection
- Automatic fallback to backup providers
- Consistent interface across providers

### 3. Lazy Tool Loading
- Tools are initialized only when needed
- Prevents circular dependencies
- Improves startup time

### 4. MCP Integration
- Model Context Protocol for standardized tool integration
- Automatic fallback to custom tools if MCP unavailable
- LangChain-compatible tool wrappers

### 5. RAG Pipeline
- Document ingestion and processing
- Vector embedding generation
- Semantic search and retrieval
- Context augmentation for LLM responses

## Data Flow

1. **User Request** → Web UI → Flask App → Chatbot
2. **Chatbot** → LangGraph Agent → Intent Detection
3. **Intent Detection** → Router → Appropriate Handler
4. **Handler** → LLM/Tools/RAG → External Services
5. **Response** → Memory Manager → Database
6. **Response** → Chatbot → Flask App → Web UI → User

## Future Architecture

See `FUTURE_ARCHITECTURE.md` for planned enhancements:
- Microservices architecture
- API Gateway and load balancing
- Real-time WebSocket communication
- Advanced caching and message queuing
- Kubernetes deployment
- Comprehensive monitoring and observability

## Documentation

### Project Structure and Design
**File:** `PROJECT_STRUCTURE_AND_DESIGN.md`

Comprehensive overview of:
- Complete project folder structure with explanations
- Architecture layers and design decisions
- Component interactions and data flow
- Design patterns used
- Testing strategy
- Deployment considerations

### Future Architecture
**File:** `FUTURE_ARCHITECTURE.md`

Planned enhancements and scalability improvements:
- Microservices architecture
- API Gateway and load balancing
- Real-time WebSocket communication
- Advanced caching and message queuing
- Kubernetes deployment

## Related Documentation

- [Agent Framework Documentation](../features/agent/AGENT_FRAMEWORK.md)
- [MCP Integration Guide](../features/mcp/MCP_INTEGRATION_SUMMARY.md)
- [RAG Service Guide](../features/rag/RAG_GUIDE.md)
- [Web UI Documentation](../features/web-ui/WEB_UI_README.md)

