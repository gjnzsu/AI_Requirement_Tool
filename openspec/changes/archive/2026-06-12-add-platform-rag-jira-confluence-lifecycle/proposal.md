## Why

Requirement Copilot currently relies on an embedded RAG implementation for Jira and Confluence knowledge capture, retrieval, and direct Jira-key lookup. A separate `ai-rag-service` is the right platform boundary, but it must first support the Jira/Confluence lifecycle explicitly so migration does not regress requirement Q&A, source grounding, or post-workflow knowledge reuse.

## What Changes

- Add a platform RAG lifecycle capability for domain-aware Jira and Confluence ingestion.
- Define a metadata contract for business fields supplied by upstream callers and technical fields owned by `ai-rag-service`.
- Add retrieval behavior that combines semantic search with optional metadata filters.
- Add Jira-key contextual retrieval so callers can answer issue-specific follow-up questions using related Jira and Confluence content.
- Add source-aware retrieval results that include document IDs, metadata, scores, and source URLs.

## Capabilities

### New Capabilities
- `platform-rag-lifecycle`: Domain-aware RAG ingestion and retrieval for Jira and Confluence knowledge, including metadata filtering, source attribution, idempotent upsert, and Jira-key contextual lookup.

### Modified Capabilities

## Impact

- Affected systems:
  - External `ai-rag-service`.
  - Vector database or retrieval backend owned by `ai-rag-service`.
- New or changed APIs:
  - Ingestion/upsert endpoint accepting content, metadata, and optional document ID.
  - Semantic retrieval endpoint accepting query, top-k, and optional metadata filters.
  - Jira-key context endpoint or equivalent filtered retrieval contract.
  - Document lookup, delete, and reindex/refresh operations.
- Dependencies:
  - Vector database metadata filtering behavior.
  - Embedding provider configuration already owned by `ai-rag-service`.
