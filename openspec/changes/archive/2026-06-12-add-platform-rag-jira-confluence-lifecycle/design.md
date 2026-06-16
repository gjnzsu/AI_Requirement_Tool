## Context

Requirement Copilot currently embeds RAG behavior through `src/rag/` and uses local embeddings, vector storage, cache, and direct vector-store document lookup for Jira/Confluence knowledge. The desired target is a separate `ai-rag-service` that owns retrieval infrastructure as a platform service.

The migration cannot be a simple transport swap because current Copilot behavior depends on Jira/Confluence-specific knowledge capture:

- workflow-created Jira issues are ingested for later retrieval;
- workflow-created Confluence pages are simplified and ingested;
- RAG queries can use a Jira key to load the exact Jira issue and related Confluence document;
- retrieved chunks are surfaced as `rag_context` for grounding/debugging.

`ai-rag-service` must therefore support Jira/Confluence lifecycle semantics before any downstream consumer switches from embedded RAG to the platform service.

## Goals / Non-Goals

**Goals:**
- Define a stable ingestion contract for Jira and Confluence documents.
- Preserve domain metadata for filtering, source attribution, relationship lookup, update, and delete operations.
- Support semantic retrieval with optional metadata filters.
- Support Jira-key contextual retrieval that returns the Jira issue and related Confluence pages.
- Keep upstream callers responsible for business metadata and context interpretation.
- Keep `ai-rag-service` responsible for chunking, embeddings, vector storage, filtering execution, ranking, and source-aware results.

**Non-Goals:**
- Change Requirement Copilot code or replace its embedded RAG integration in this phase.
- Require `ai-rag-service` to create Jira issues or Confluence pages.
- Require embedding models to infer business metadata.
- Replace post-Jira maturity evaluation or pre-Jira quality gates.
- Define the final rollout plan for switching Copilot traffic from embedded to external RAG.

## Decisions

### Decision: Use an explicit metadata contract

Upstream callers will send business metadata with each ingestion request. The RAG service will validate and preserve those fields, then add technical metadata during indexing.

Business metadata examples:
- `type`: `jira_issue` or `confluence_page`
- `key`: Jira issue key for Jira documents
- `related_jira`: Jira issue key associated with a Confluence page
- `title`
- `url`
- `project_key`
- `space_key`
- `status`
- `priority`
- `source`

Technical metadata examples owned by `ai-rag-service`:
- `document_id`
- `chunk_id`
- `chunk_index`
- `content_hash`
- `ingested_at`
- `updated_at`
- `embedding_model`
- `schema_version`

Rationale: upstream business services already know Jira keys, Confluence links, project, and workflow context. The RAG service knows indexing internals. Keeping both sides explicit avoids brittle metadata inference.

Alternative considered: let `ai-rag-service` infer metadata from content. This was rejected because issue keys, project scopes, source URLs, and relationship intent are more reliable when supplied by the business workflow.

### Decision: Support idempotent document upsert

Ingestion will be an upsert keyed by `document_id` when provided. Callers can use stable IDs such as `jira_issue:PROJ-123` and `confluence_page:<page-or-derived-id>`. If no ID is provided, `ai-rag-service` may derive one from metadata and content hash.

Rationale: Jira and Confluence content changes over time. Upsert avoids duplicate chunks and lets future workflow runs refresh the searchable record.

Alternative considered: append-only ingestion. This was rejected because stale requirement knowledge would accumulate and reduce answer quality.

### Decision: Put metadata filtering in retrieval APIs

The retrieval API will accept optional filters and apply them in the vector database or retrieval backend. Embedding generation will only produce vectors; it will not apply or infer filters.

Rationale: Metadata filtering is a retrieval concern, not an embedding concern. This keeps behavior explainable and backend-portable across Chroma, Qdrant, Pinecone, pgvector, OpenSearch, or another store.

Alternative considered: require callers to prefetch documents and send only text to RAG. This was rejected because it leaks storage/retrieval responsibility back into upstream services.

### Decision: Add a first-class Jira-key context retrieval path

`ai-rag-service` will support either a dedicated endpoint such as `GET /context/by-jira-key/{key}` or an equivalent filtered retrieval request. It must return the Jira issue document and related Confluence documents when available.

Rationale: Current embedded RAG has direct Jira-key behavior. Preserving this as an explicit contract prevents regressions for issue-specific follow-up questions.

Alternative considered: rely only on semantic search for Jira-key questions. This was rejected because exact issue lookup should not depend on embedding similarity.

## Risks / Trade-offs

- Service unavailable -> Callers must decide whether to fail, retry, or degrade gracefully; `ai-rag-service` should return clear timeout/unavailable responses.
- Metadata contract drift -> Version metadata with `schema_version`, validate known required fields, and add contract tests for the public API.
- Filter semantics vary by vector backend -> Keep the public filter model small at first: equality, `in`, and relationship lookups by Jira key.
- Duplicate or stale content -> Use stable document IDs, content hashes, and upsert semantics.
- Permissions and tenant isolation are easy to forget -> Reserve `tenant_id`, `project_key`, `space_key`, and access metadata in the contract even if enforcement is phased.
- Retrieval quality may differ from embedded implementations -> Provide representative contract and quality tests before consumers migrate.

## Migration Plan

1. Add `ai-rag-service` endpoints for document upsert, semantic retrieval with filters, document lookup, and Jira-key context lookup.
2. Add contract tests around Jira issue ingestion, Confluence page ingestion, metadata filtering, source attribution, and Jira-key lookup.
3. Add service-level smoke tests against the selected vector backend.
4. Publish the API and metadata contract for downstream consumers.
5. Defer consumer-side migration, including Requirement Copilot adapter work, to a separate follow-up change after service parity is verified.

Rollback: disable the new Jira/Confluence lifecycle endpoints or route callers back to existing RAG behavior while preserving existing indexed data.

## Open Questions

- What authentication mechanism will callers use when calling `ai-rag-service`?
- Should `ai-rag-service` enforce tenant/project/space permissions in the first release or only preserve metadata for future enforcement?
- Should Confluence document IDs use page ID, URL hash, Jira key plus title, or a service-generated ID returned to callers?
- Should Jira-key context retrieval return exact documents only, or exact documents plus semantically similar supporting chunks?
