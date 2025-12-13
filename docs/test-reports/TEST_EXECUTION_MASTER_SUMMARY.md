# Test Execution Master Summary

**Generated:** 2025-12-13 12:55:31  
**Execution Mode:** Parallel
**Wall-Clock Time (Actual):** 169.65 seconds (2.8 minutes)
**Sum of Test Times:** 471.34 seconds (7.9 minutes)  
**Parallel Speedup:** 2.78x  
**Total Tests:** 78  
**Passed:** 73 [PASS]  
**Failed:** 5  
**Categories:** 7

## Summary by Category

| Category | Tests | Passed | Failed | Execution Time | Avg Time/Test |
|----------|-------|--------|--------|----------------|---------------|
| **AGENT** | 2 | 2 | 0 | 103.87s | 51.94s |
| **API** | 37 | 34 | 3 | 28.10s | 0.76s |
| **LLM** | 3 | 3 | 0 | 20.97s | 6.99s |
| **MCP** | 26 | 24 | 2 | 167.93s | 6.46s |
| **MEMORY** | 2 | 2 | 0 | 59.23s | 29.61s |
| **RAG** | 6 | 6 | 0 | 83.35s | 13.89s |
| **UNIT** | 2 | 2 | 0 | 7.89s | 3.94s |

## Slowest Tests Across All Categories

| Rank | Test Case | Category | Execution Time | Percentage |
|------|-----------|----------|----------------|------------|
| 1 | `test_agent` | agent | **66.58s** | 14.1% |
| 2 | `test_rag_chatbot` | rag | **45.65s** | 9.7% |
| 3 | `test_mcp_jira_direct` | mcp | **34.48s** | 7.3% |
| 4 | `test_chatbot_integration` | memory | **21.34s** | 4.5% |
| 5 | `test_0_health_check_confluence_mcp_server` | mcp | **18.76s** | 4.0% |
| 6 | `test_chatbot_with_rag` | rag | **17.14s** | 3.6% |
| 7 | `test_confluence_mcp_server` | mcp | **16.05s** | 3.4% |
| 8 | `test_deepseek_chatbot` | agent | **14.04s** | 3.0% |
| 9 | `test_deepseek_api` | llm | **7.31s** | 1.6% |
| 10 | `test_rag_ingestion` | rag | **6.01s** | 1.3% |

## Overall Statistics

- **Wall-Clock Time (Actual):** 169.65 seconds (2.8 minutes)
- **Sum of Test Times:** 471.34 seconds (7.9 minutes)
- **Parallel Speedup:** 2.78x (tests ran 2.8x faster due to parallelism)
- **Average Time per Test:** 6.04s (78 tests)
- **Success Rate:** 93.6% (73/78)
- **Categories Tested:** 7
- **Execution Mode:** Parallel
- **Max Parallel Workers:** 4

## Recommendations

- [WARN] 5 test(s) failed - review and fix
- [SLOW] Slowest test: `test_agent` (66.58s) - consider optimization
- [TIME] Total execution time is 7.9 minutes - parallel execution already enabled

## Category Reports

For detailed reports, see:
- **[AGENT](../../tests/integration/agent/TEST_EXECUTION_SUMMARY.md)**
- **[API](../../tests/integration/api/TEST_EXECUTION_SUMMARY.md)**
- **[LLM](../../tests/integration/llm/TEST_EXECUTION_SUMMARY.md)**
- **[MCP](../../tests/integration/mcp/TEST_EXECUTION_SUMMARY.md)**
- **[MEMORY](../../tests/integration/memory/TEST_EXECUTION_SUMMARY.md)**
- **[RAG](../../tests/integration/rag/TEST_EXECUTION_SUMMARY.md)**
- **[UNIT](../../tests/unit/TEST_EXECUTION_SUMMARY.md)**
