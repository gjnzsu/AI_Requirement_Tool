# LLM Tests - Execution Time Summary

**Test Run Date:** 2025-12-13 12:53:05  
**Execution Mode:** Parallel (4 workers)
**Total Execution Time:** 20.97 seconds  
**Total Tests:** 3  
**Passed:** 3 [PASS]  
**Failed:** 0  
**Warnings:** 11 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_deepseek_api` | **7.31s** | [PASS] PASSED | |
| `test_openai_api` | **5.30s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 20.97 seconds
- **Average Time:** 6.30 seconds
- **Slowest Test:** `test_deepseek_api` (7.31s)
- **Fastest Test:** `test_openai_api` (5.30s)

### Test Results
- **Passed:** 3
- **Failed:** 0
- **Warnings:** 11
- **Parallel Workers:** 4

## Performance Analysis

### Slowest Test
- **test_deepseek_api** (7.31s) - 34.9% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest llm -v --durations=0 --tb=short -n=4
```

## Recommendations

- Consider optimizing `test_deepseek_api` (takes 7.31s)
- 11 warnings detected - review for potential issues
