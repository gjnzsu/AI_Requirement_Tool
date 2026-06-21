## Why

Requirement Copilot still constructs and uses the embedded RAG implementation even though `ai-rag-service` now exposes platform lifecycle APIs for Jira and Confluence knowledge. Migrating Copilot behind RAG ports lets the product use the platform service while preserving embedded RAG as a safe fallback during rollout.

## What Changes

- Add application-facing RAG query and ingestion ports that hide embedded vs external provider details.
- Add an external HTTP adapter for `ai-rag-service` lifecycle APIs.
- Add an embedded adapter that wraps the current local `RAGService` for compatibility and rollback.
- Configure RAG provider selection with environment/runtime settings.
- Update RAG query flow to use port methods instead of direct `vector_store` access.
- Update Jira/Confluence workflow ingestion to send platform metadata to the selected RAG provider.
- Preserve existing behavior when embedded RAG is selected or external RAG is unavailable.

## Capabilities

### New Capabilities
- `requirement-copilot-platform-rag`: Requirement Copilot can use external platform RAG for Jira/Confluence ingestion and retrieval while preserving embedded fallback and existing user-facing behavior.

### Modified Capabilities

## Impact

- Affected code areas:
  - `config/config.py`
  - `src/chatbot.py`
  - `src/runtime/composition.py`
  - `src/services/rag_query_service.py`
  - `src/services/rag_ingestion_service.py`
  - `src/application/ports/`
  - new `src/adapters/rag/`
  - tests for runtime composition, RAG query, RAG ingestion, and requirement workflow progress
- Affected external API:
  - `ai-rag-service` lifecycle endpoints:
    - `POST /documents/upsert`
    - `POST /retrieve`
    - `GET /documents/{document_id}`
    - `GET /context/jira/{jira_key}`
    - `DELETE /documents/{document_id}`
- Runtime configuration:
  - `RAG_PROVIDER=embedded|external`
  - `AI_RAG_SERVICE_URL`
  - `AI_RAG_SERVICE_TIMEOUT_SECONDS`
  - optional service auth settings if required later
