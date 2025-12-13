# MEMORY Tests - Execution Time Summary

**Test Run Date:** 2025-12-13 12:53:43  
**Execution Mode:** Parallel (4 workers)
**Total Execution Time:** 59.23 seconds  
**Total Tests:** 2  
**Passed:** 2 [PASS]  
**Failed:** 0  
**Warnings:** 10 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_chatbot_integration` | **21.34s** | [PASS] PASSED | |
| `test_memory_manager` | **0.16s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 59.23 seconds
- **Average Time:** 10.75 seconds
- **Slowest Test:** `test_chatbot_integration` (21.34s)
- **Fastest Test:** `test_memory_manager` (0.16s)

### Test Results
- **Passed:** 2
- **Failed:** 0
- **Warnings:** 10
- **Parallel Workers:** 4

## Performance Analysis

### Slowest Test
- **test_chatbot_integration** (21.34s) - 36.0% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest memory -v --durations=0 --tb=short -n=4
```

## Recommendations

- Consider optimizing `test_chatbot_integration` (takes 21.34s)
- 10 warnings detected - review for potential issues
