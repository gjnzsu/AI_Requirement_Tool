# RAG Tests - Execution Time Summary

**Test Run Date:** 2025-12-13 12:54:07  
**Execution Mode:** Parallel (4 workers)
**Total Execution Time:** 83.35 seconds  
**Total Tests:** 6  
**Passed:** 6 [PASS]  
**Failed:** 0  
**Warnings:** 9 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_rag_chatbot` | **45.65s** | [PASS] PASSED | |
| `test_chatbot_with_rag` | **17.14s** | [PASS] PASSED | |
| `test_rag_ingestion` | **6.01s** | [PASS] PASSED | |
| `test_rag_retrieval` | **0.15s** | [PASS] PASSED | |
| `test_rag_retrieval` | **0.13s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 83.35 seconds
- **Average Time:** 13.82 seconds
- **Slowest Test:** `test_rag_chatbot` (45.65s)
- **Fastest Test:** `test_rag_retrieval` (0.13s)

### Test Results
- **Passed:** 6
- **Failed:** 0
- **Warnings:** 9
- **Parallel Workers:** 4

## Performance Analysis

### Slowest Test
- **test_rag_chatbot** (45.65s) - 54.8% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest rag -v --durations=0 --tb=short -n=4
```

## Recommendations

- Consider optimizing `test_rag_chatbot` (takes 45.65s)
- 9 warnings detected - review for potential issues
