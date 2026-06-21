## Context

Requirement Copilot currently initializes `src.rag.RAGService` directly in `src/chatbot.py` and passes the concrete service through agent, workflow, query, and ingestion services. Query flow also reaches into `rag_service.vector_store` for direct Jira-key context lookup. This makes RAG infrastructure an embedded product concern instead of a platform service dependency.

`ai-rag-service` now exposes lifecycle APIs for document upsert, metadata-filtered retrieval, document lookup, and Jira-key contextual retrieval. Requirement Copilot can migrate to that platform service by introducing RAG ports and adapters while preserving embedded fallback.

## Goals / Non-Goals

**Goals:**
- Hide embedded vs external RAG behind application-facing ports.
- Support external `ai-rag-service` for Jira/Confluence ingestion and retrieval.
- Preserve existing embedded RAG behavior behind the same contracts.
- Remove direct `vector_store` access from RAG query flow.
- Preserve current Jira/Confluence workflow behavior and user-facing responses.
- Degrade gracefully when external RAG is unavailable for non-critical ingestion.

**Non-Goals:**
- Remove `src/rag/` in this change.
- Change `ai-rag-service` APIs.
- Migrate AI Market Studio or other consumers.
- Change intent routing semantics for RAG vs general chat.
- Make RAG mandatory for Jira or Confluence creation.

## Decisions

### Decision: Add separate query and ingestion ports

Create a `RagQueryPort` for retrieval and context lookup, and update/use `RagIngestionPort` for knowledge ingestion. Services will depend on these ports rather than a concrete embedded service.

Rationale: query and ingestion have different failure handling and response shapes. Separate ports keep the contracts smaller and make tests easier.

Alternative considered: keep passing a single duck-typed `rag_service`. This was rejected because current code already leaks implementation details such as `vector_store`.

### Decision: Use adapters for embedded and external providers

Add:
- `EmbeddedRagAdapter` wrapping current `RAGService`.
- `ExternalRagAdapter` calling `ai-rag-service` lifecycle endpoints.

Rationale: the runtime can switch providers without changing workflow or query services.

Alternative considered: replace embedded calls directly with HTTP calls. This was rejected because it would make rollback harder and preserve provider-specific logic in service code.

### Decision: Model external retrieval around lifecycle endpoints

External adapter behavior:
- `ingest(content, metadata)` -> `POST /documents/upsert`
- `retrieve(query, top_k, filters)` -> `POST /retrieve`
- `get_context(query, top_k)` -> `POST /retrieve`, joining returned content
- `get_jira_context(jira_key)` -> `GET /context/jira/{jira_key}`

Rationale: this maps current Copilot needs to platform APIs while preserving source-aware payloads.

Alternative considered: continue using legacy `/query` on `ai-rag-service`. This was rejected because `/query` generates an answer, while Copilot needs retrieved context to build its own prompt.

### Decision: Keep business metadata generation in Copilot

Requirement workflow and ingestion helper code will continue to shape business metadata such as `type`, `key`, `related_jira`, `title`, `url`, `project_key`, `space_key`, `status`, and `priority`.

Rationale: Copilot knows the workflow object and Atlassian context. The platform RAG service should not infer those fields from text.

### Decision: Add runtime provider selection

Configuration will select:
- `embedded`: initialize current local RAG behavior.
- `external`: initialize HTTP adapter for `ai-rag-service`.

If external configuration is missing or unavailable during initialization, Copilot should either disable RAG or fall back according to an explicit configuration decision.

Rationale: migration needs staged rollout and simple rollback.

## Risks / Trade-offs

- External service timeout -> Use short adapter timeouts and preserve non-blocking ingestion behavior.
- Retrieval parity differences -> Add tests for Jira-key context and metadata-filtered retrieval; run staging comparison before production default switch.
- Metadata mismatch -> Keep metadata generation centralized in `RagIngestionService` and add adapter contract tests.
- Source payload shape mismatch -> Normalize external retrieval results into the existing `rag_context` shape for agent state.
- Hidden embedded dependencies -> Remove `vector_store` access from service code and move any embedded-specific lookup into the embedded adapter.

## Migration Plan

1. Add RAG query and ingestion port contracts.
2. Add embedded adapter around current `RAGService`.
3. Add external HTTP adapter around `ai-rag-service` lifecycle endpoints.
4. Update runtime composition and chatbot/agent initialization to select provider by configuration.
5. Update RAG query and ingestion services to depend on ports.
6. Add unit tests for embedded provider, external provider, timeout handling, and provider selection.
7. Run staging parity checks for Jira issue lookup, related Confluence lookup, metadata-filtered retrieval, and non-critical ingestion failure.
8. Switch default provider only after parity is accepted.

Rollback: set `RAG_PROVIDER=embedded` or disable RAG while preserving Jira/Confluence creation.

## Open Questions

- Should external RAG initialization fall back to embedded automatically or fail closed when `RAG_PROVIDER=external` is configured incorrectly?
- What auth header or token should Requirement Copilot use for `ai-rag-service` in non-local environments?
- Should external retrieval source metadata be surfaced in the UI now, or only preserved in backend state for debugging?
