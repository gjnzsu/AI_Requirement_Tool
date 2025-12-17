# RAG Tests - Execution Time Summary

**Test Run Date:** 2025-12-16 22:37:44  
**Total Execution Time:** 91.99 seconds  
**Total Tests:** 6  
**Passed:** 6 [PASS]  
**Failed:** 0  
**Warnings:** 3 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_rag_chatbot` | **68.62s** | [PASS] PASSED | |
| `test_chatbot_with_rag` | **12.33s** | [PASS] PASSED | |
| `test_rag_retrieval` | **6.22s** | [PASS] PASSED | |
| `test_rag_ingestion` | **4.80s** | [PASS] PASSED | |
| `test_rag_retrieval` | **0.02s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 91.99 seconds
- **Average Time:** 18.40 seconds
- **Slowest Test:** `test_rag_chatbot` (68.62s)
- **Fastest Test:** `test_rag_retrieval` (0.02s)

### Test Results
- **Passed:** 6
- **Failed:** 0
- **Warnings:** 3

## Performance Analysis

### Slowest Test
- **test_rag_chatbot** (68.62s) - 74.6% of total execution time
  - May include network latency, API calls, or complex operations

### Fastest Test
- **test_rag_retrieval** (0.02s) - Instant execution
  - Likely using mocked responses or simple operations


## Command Used

```bash
python -m pytest rag -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_rag_chatbot` (takes 68.62s)
