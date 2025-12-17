# Test Execution Master Summary

**Generated:** 2025-12-16 22:39:41  
**Total Execution Time:** 182.25 seconds  
**Total Tests:** 52  
**Passed:** 49 [PASS]  
**Failed:** 3  
**Categories:** 7

## Summary by Category

| Category | Tests | Passed | Failed | Execution Time | Avg Time/Test |
|----------|-------|--------|--------|----------------|---------------|
| **AGENT** | 2 | 2 | 0 | 56.65s | 28.32s |
| **API** | 37 | 34 | 3 | 0.37s | 0.01s |
| **LLM** | 3 | 3 | 0 | 9.59s | 3.20s |
| **MCP** | 0 | 0 | 0 | 0.00s | 0.00s |
| **MEMORY** | 2 | 2 | 0 | 23.60s | 11.80s |
| **RAG** | 6 | 6 | 0 | 91.99s | 15.33s |
| **UNIT** | 2 | 2 | 0 | 0.05s | 0.03s |

## Slowest Tests Across All Categories

| Rank | Test Case | Category | Execution Time | Percentage |
|------|-----------|----------|----------------|------------|
| 1 | `test_rag_chatbot` | rag | **68.62s** | 37.7% |
| 2 | `test_agent` | agent | **46.18s** | 25.3% |
| 3 | `test_chatbot_integration` | memory | **15.56s** | 8.5% |
| 4 | `test_chatbot_with_rag` | rag | **12.33s** | 6.8% |
| 5 | `test_deepseek_chatbot` | agent | **10.47s** | 5.7% |
| 6 | `test_deepseek_api` | llm | **6.37s** | 3.5% |
| 7 | `test_rag_retrieval` | rag | **6.22s** | 3.4% |
| 8 | `test_openai_api` | llm | **2.11s** | 1.2% |
| 9 | `test_memory_manager` | memory | **0.03s** | 0.0% |
| 10 | `test_chat_success` | api | **0.01s** | 0.0% |

## Overall Statistics

- **Total Execution Time:** 182.25 seconds (3.0 minutes)
- **Average Time per Test:** 3.50s (52 tests)
- **Success Rate:** 94.2% (49/52)
- **Categories Tested:** 7

## Recommendations

- [WARN] 3 test(s) failed - review and fix
- [SLOW] Slowest test: `test_rag_chatbot` (68.62s) - consider optimization

## Category Reports

For detailed reports, see:
- **[AGENT](../../tests/integration/agent/TEST_EXECUTION_SUMMARY.md)**
- **[API](../../tests/integration/api/TEST_EXECUTION_SUMMARY.md)**
- **[LLM](../../tests/integration/llm/TEST_EXECUTION_SUMMARY.md)**
- **[MCP](../../tests/integration/mcp/TEST_EXECUTION_SUMMARY.md)**
- **[MEMORY](../../tests/integration/memory/TEST_EXECUTION_SUMMARY.md)**
- **[RAG](../../tests/integration/rag/TEST_EXECUTION_SUMMARY.md)**
- **[UNIT](../../tests/unit/TEST_EXECUTION_SUMMARY.md)**
