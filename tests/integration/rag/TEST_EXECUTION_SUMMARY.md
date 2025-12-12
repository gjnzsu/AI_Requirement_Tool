# RAG Tests - Execution Time Summary

**Test Run Date:** 2025-12-12 15:20:30  
**Total Execution Time:** 0.00 seconds  
**Total Tests:** 6  
**Passed:** 6 [PASS]  
**Failed:** 0  
**Warnings:** 3 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_rag_chatbot` | **64.00s** | [PASS] PASSED | |
| `test_chatbot_with_rag` | **13.12s** | [PASS] PASSED | |
| `test_rag_ingestion` | **5.71s** | [PASS] PASSED | |
| `test_rag_retrieval` | **0.05s** | [PASS] PASSED | |
| `test_rag_retrieval` | **0.04s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 0.00 seconds
- **Average Time:** 16.58 seconds
- **Slowest Test:** `test_rag_chatbot` (64.00s)
- **Fastest Test:** `test_rag_retrieval` (0.04s)

### Test Results
- **Passed:** 6
- **Failed:** 0
- **Warnings:** 3

## Performance Analysis

### Slowest Test
- **test_rag_chatbot** (64.00s) - 0.0% of total execution time
  - May include network latency, API calls, or complex operations

### Fastest Test
- **test_rag_retrieval** (0.04s) - Instant execution
  - Likely using mocked responses or simple operations


## Command Used

```bash
python -m pytest rag -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_rag_chatbot` (takes 64.00s)
