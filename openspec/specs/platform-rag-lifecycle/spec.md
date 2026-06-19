# platform-rag-lifecycle Specification

## Purpose
TBD - created by archiving change add-platform-rag-jira-confluence-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: Domain-aware document ingestion
The system SHALL allow callers to ingest Jira and Confluence knowledge into `ai-rag-service` with content, business metadata, and an optional stable document ID.

#### Scenario: Jira issue is ingested with business metadata
- **WHEN** a caller sends a Jira issue document with content, document ID `jira_issue:PROJ-123`, and metadata containing `type`, `key`, `project_key`, `title`, `url`, `status`, and `priority`
- **THEN** `ai-rag-service` SHALL persist the document, preserve the supplied business metadata, add technical indexing metadata, and make the document retrievable by document ID and Jira key

#### Scenario: Confluence page is ingested with Jira relationship metadata
- **WHEN** a caller sends a Confluence page document with content and metadata containing `type`, `title`, `url`, `space_key`, and `related_jira`
- **THEN** `ai-rag-service` SHALL persist the document, preserve the relationship to the Jira key, and make the document retrievable by metadata filters and Jira-key context lookup

#### Scenario: Ingestion accepts service-generated document IDs
- **WHEN** a caller sends content and valid business metadata without a document ID
- **THEN** `ai-rag-service` SHALL assign a stable document ID, return it in the ingestion response, and store it with indexed chunks

### Requirement: Idempotent document upsert
The system SHALL support idempotent upsert for ingested Jira and Confluence documents.

#### Scenario: Existing document is updated
- **WHEN** a caller ingests a document using a document ID that already exists
- **THEN** `ai-rag-service` SHALL replace or refresh the indexed representation for that document instead of creating duplicate active documents

#### Scenario: Repeated ingestion of unchanged content is safe
- **WHEN** a caller submits the same document ID and equivalent content multiple times
- **THEN** `ai-rag-service` SHALL return a successful response without creating duplicate searchable chunks

### Requirement: Metadata filter retrieval
The system SHALL support retrieval requests that combine semantic query search with optional metadata filters.

#### Scenario: Retrieval is constrained by metadata filters
- **WHEN** a caller sends a retrieval request with a natural-language query and filters such as `type = jira_issue` and `project_key = PROJ`
- **THEN** `ai-rag-service` SHALL return semantically relevant chunks only from documents matching the supplied filters

#### Scenario: Retrieval works without filters
- **WHEN** a caller sends a retrieval request with a natural-language query and no metadata filters
- **THEN** `ai-rag-service` SHALL perform semantic retrieval across the caller's allowed knowledge scope

#### Scenario: Unsupported filters are rejected clearly
- **WHEN** a caller sends a retrieval request containing unsupported filter operators or malformed filter values
- **THEN** `ai-rag-service` SHALL reject the request with a clear validation error and MUST NOT silently ignore the unsupported filters

### Requirement: Jira-key contextual retrieval
The system SHALL support exact Jira-key contextual retrieval for issue-specific questions.

#### Scenario: Jira key returns issue and related Confluence context
- **WHEN** a caller requests context for Jira key `PROJ-123`
- **THEN** `ai-rag-service` SHALL return the `jira_issue:PROJ-123` document when present and Confluence documents whose metadata relates them to `PROJ-123`

#### Scenario: Missing Jira key returns an empty contextual result
- **WHEN** a caller requests context for a Jira key that has no indexed Jira or related Confluence documents
- **THEN** `ai-rag-service` SHALL return an empty successful result or a documented not-found response that callers can treat as no RAG context

#### Scenario: Jira-key context does not rely on semantic similarity alone
- **WHEN** a document has exact metadata relationship to `PROJ-123` but low semantic similarity to the user's query text
- **THEN** `ai-rag-service` SHALL still include that document in Jira-key contextual retrieval according to the context endpoint contract

### Requirement: Source-aware retrieval results
The system SHALL return retrieval results with enough source data for callers to ground answers and debug retrieval.

#### Scenario: Retrieval result includes source fields
- **WHEN** `ai-rag-service` returns a retrieved chunk
- **THEN** the result SHALL include chunk content, score or rank, document ID, chunk ID, preserved metadata, and source URL when available

#### Scenario: Caller can preserve retrieval context
- **WHEN** a caller receives source-aware retrieval results
- **THEN** it SHALL be able to build grounded downstream prompts from chunk content and preserve source data for debugging or attribution

### Requirement: Delete and reindex lifecycle operations
The system SHALL provide lifecycle operations for deleting or refreshing indexed Jira and Confluence knowledge.

#### Scenario: Document can be deleted by document ID
- **WHEN** a caller requests deletion of an indexed document by document ID
- **THEN** `ai-rag-service` SHALL remove active searchable chunks for that document

#### Scenario: Related knowledge can be refreshed by Jira key
- **WHEN** a caller requests reindexing for a Jira key
- **THEN** `ai-rag-service` SHALL support refreshing or replacing the active indexed records associated with that Jira key

