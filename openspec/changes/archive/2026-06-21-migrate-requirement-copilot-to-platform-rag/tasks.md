## 1. Port Contracts

- [x] 1.1 Add `RagQueryPort` protocol covering semantic retrieval, joined context retrieval, and Jira-key context lookup.
- [x] 1.2 Update or confirm `RagIngestionPort` covers content, metadata, and document ID return behavior.
- [x] 1.3 Add shared result types for retrieved chunks and ingestion responses if needed by adapters.

## 2. RAG Adapters

- [x] 2.1 Add `src/adapters/rag/` package.
- [x] 2.2 Implement embedded RAG adapter around the existing `src.rag.RAGService`.
- [x] 2.3 Move embedded direct Jira-key vector-store lookup behind the embedded query adapter.
- [x] 2.4 Implement external HTTP RAG adapter for `POST /documents/upsert`, `POST /retrieve`, `GET /context/jira/{jira_key}`, and document lookup.
- [x] 2.5 Add adapter timeout handling and controlled error mapping.
- [x] 2.6 Add unit tests for embedded and external adapter success, empty results, validation errors, and timeouts.

## 3. Runtime Configuration And Composition

- [x] 3.1 Add `RAG_PROVIDER`, `AI_RAG_SERVICE_URL`, and `AI_RAG_SERVICE_TIMEOUT_SECONDS` configuration values.
- [x] 3.2 Add a RAG provider factory or composition helper that returns query and ingestion ports.
- [x] 3.3 Update `Chatbot` initialization to create selected RAG ports instead of directly constructing only embedded `RAGService`.
- [x] 3.4 Update `ChatbotAgent` and `build_application_services` composition to receive RAG ports.
- [x] 3.5 Preserve current embedded behavior when `RAG_PROVIDER` is unset or `embedded`.

## 4. Service Integration

- [x] 4.1 Update `RagQueryService` to use `RagQueryPort` and remove direct `rag_service.vector_store` access.
- [x] 4.2 Update `RagIngestionService` to use `RagIngestionPort` while preserving metadata shaping and timeout behavior.
- [x] 4.3 Update requirement workflow RAG ingestion calls to include platform metadata required by `ai-rag-service`.
- [x] 4.4 Preserve user-facing RAG error messages and fallback behavior.

## 5. Tests And Verification

- [x] 5.1 Add runtime composition tests for embedded provider selection.
- [x] 5.2 Add runtime composition tests for external provider selection.
- [x] 5.3 Update RAG query service tests to verify Jira-key context lookup goes through the query port.
- [x] 5.4 Update RAG ingestion service tests to verify external-style metadata and returned document IDs.
- [x] 5.5 Add requirement workflow tests for external RAG ingestion success and non-blocking failure.
- [x] 5.6 Run focused RAG, workflow, and runtime test suites.
- [x] 5.7 Add opt-in external RAG pipeline e2e coverage for Jira-key retrieval, related Confluence retrieval, metadata-filtered retrieval, and non-blocking failure.

## 6. Rollout Notes

- [x] 6.1 Document local/staging configuration for external RAG.
- [x] 6.2 Document rollback to `RAG_PROVIDER=embedded`.
- [x] 6.3 Document parity smoke scenarios for Jira-key context, related Confluence context, metadata-filtered retrieval, and ingestion timeout.
- [x] 6.4 Document opt-in external RAG pipeline e2e command and write behavior.
