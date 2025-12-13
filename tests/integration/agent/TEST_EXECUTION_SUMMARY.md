# AGENT Tests - Execution Time Summary

**Test Run Date:** 2025-12-13 12:54:27  
**Execution Mode:** Parallel (4 workers)
**Total Execution Time:** 103.87 seconds  
**Total Tests:** 2  
**Passed:** 2 [PASS]  
**Failed:** 0  
**Warnings:** 9 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_agent` | **66.58s** | [PASS] PASSED | |
| `test_deepseek_chatbot` | **14.04s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 103.87 seconds
- **Average Time:** 40.31 seconds
- **Slowest Test:** `test_agent` (66.58s)
- **Fastest Test:** `test_deepseek_chatbot` (14.04s)

### Test Results
- **Passed:** 2
- **Failed:** 0
- **Warnings:** 9
- **Parallel Workers:** 4

## Performance Analysis

### Slowest Test
- **test_agent** (66.58s) - 64.1% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest agent -v --durations=0 --tb=short -n=4
```

## Recommendations

- Consider optimizing `test_agent` (takes 66.58s)
- 9 warnings detected - review for potential issues
