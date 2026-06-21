# requirement-copilot-platform-rag Specification

## Purpose
Define how Requirement Copilot selects embedded versus platform RAG, routes retrieval and ingestion through application ports, and degrades safely when `ai-rag-service` is unavailable.
## Requirements
### Requirement: Configurable RAG provider
Requirement Copilot SHALL support runtime selection between embedded RAG and external platform RAG.

#### Scenario: Embedded provider preserves existing behavior
- **WHEN** `RAG_PROVIDER` is unset or set to `embedded`
- **THEN** Requirement Copilot SHALL use the local embedded RAG implementation behind the RAG ports

#### Scenario: External provider uses ai-rag-service
- **WHEN** `RAG_PROVIDER` is set to `external` and `AI_RAG_SERVICE_URL` is configured
- **THEN** Requirement Copilot SHALL use the external RAG adapter for ingestion and retrieval

#### Scenario: RAG can be disabled
- **WHEN** RAG is disabled by existing configuration
- **THEN** Requirement Copilot SHALL skip RAG initialization and preserve current non-RAG behavior

### Requirement: RAG query port usage
Requirement Copilot SHALL perform RAG retrieval through an application-facing query port.

#### Scenario: RAG query builds prompt from retrieved context
- **WHEN** a user request is routed to RAG query handling and the selected provider returns context
- **THEN** Requirement Copilot SHALL build the grounded prompt from retrieved context and generate the assistant response

#### Scenario: Jira-key query uses provider context lookup
- **WHEN** a RAG query contains a Jira key such as `PROJ-123`
- **THEN** Requirement Copilot SHALL request Jira-key context through the query port instead of directly accessing a vector store

#### Scenario: Missing RAG context falls back to normal prompt
- **WHEN** the selected RAG provider returns no context
- **THEN** Requirement Copilot SHALL continue response generation without RAG context using the original user input

### Requirement: RAG ingestion port usage
Requirement Copilot SHALL perform Jira and Confluence knowledge ingestion through an application-facing ingestion port.

#### Scenario: Jira issue ingestion sends platform metadata
- **WHEN** Requirement Copilot ingests a Jira issue into RAG
- **THEN** it SHALL send content with metadata that includes `type`, `key`, `title`, `url`, `project_key`, `status`, and `priority` when available

#### Scenario: Confluence page ingestion sends relationship metadata
- **WHEN** Requirement Copilot ingests a Confluence page into RAG
- **THEN** it SHALL send content with metadata that includes `type`, `title`, `url`, `space_key`, and `related_jira` when available

#### Scenario: Ingestion returns document identifier
- **WHEN** the selected RAG provider successfully ingests content
- **THEN** Requirement Copilot SHALL preserve the returned document identifier in workflow progress or debug state where existing behavior exposes RAG ingestion detail

### Requirement: External RAG adapter contract
Requirement Copilot SHALL normalize external `ai-rag-service` lifecycle responses into its internal RAG query and ingestion shapes.

#### Scenario: External retrieval maps source-aware chunks
- **WHEN** `ai-rag-service` returns retrieval results with content, document ID, chunk ID, metadata, score, and source URL
- **THEN** the external adapter SHALL expose chunk content for prompt construction and preserve source metadata for `rag_context` or equivalent debug state

#### Scenario: External ingestion maps upsert response
- **WHEN** `ai-rag-service` returns a document upsert response
- **THEN** the external adapter SHALL return the document ID to the ingestion service

#### Scenario: External adapter validates request failures
- **WHEN** `ai-rag-service` returns a validation error
- **THEN** the external adapter SHALL surface a controlled failure that does not crash the agent graph

### Requirement: Graceful degradation
Requirement Copilot SHALL degrade gracefully when selected RAG provider calls fail.

#### Scenario: Non-critical ingestion timeout does not block workflow
- **WHEN** RAG ingestion times out during Jira or Confluence workflow execution
- **THEN** Requirement Copilot SHALL mark RAG ingestion as failed or skipped without failing successful Jira or Confluence creation

#### Scenario: Retrieval failure does not crash chat response
- **WHEN** RAG retrieval fails due to timeout, service unavailable, or provider error
- **THEN** Requirement Copilot SHALL continue with a safe response path and avoid exposing raw stack traces to the user

### Requirement: Migration parity tests
Requirement Copilot SHALL include tests that verify embedded and external RAG provider behavior for key Jira/Confluence scenarios.

#### Scenario: Provider selection is tested
- **WHEN** runtime composition is tested with embedded and external RAG settings
- **THEN** tests SHALL verify that the correct adapter is selected

#### Scenario: Jira-key context parity is tested
- **WHEN** RAG query service is tested with a Jira-key question
- **THEN** tests SHALL verify that context lookup occurs through the query port and not through direct vector-store access

#### Scenario: External failure handling is tested
- **WHEN** the external adapter times out or returns unavailable responses in tests
- **THEN** tests SHALL verify graceful degradation for query and ingestion flows
