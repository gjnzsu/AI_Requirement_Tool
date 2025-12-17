# LLM Tests - Execution Time Summary

**Test Run Date:** 2025-12-16 22:35:36  
**Total Execution Time:** 9.59 seconds  
**Total Tests:** 3  
**Passed:** 3 [PASS]  
**Failed:** 0  
**Warnings:** 5 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_deepseek_api` | **6.37s** | [PASS] PASSED | |
| `test_openai_api` | **2.11s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 9.59 seconds
- **Average Time:** 4.24 seconds
- **Slowest Test:** `test_deepseek_api` (6.37s)
- **Fastest Test:** `test_openai_api` (2.11s)

### Test Results
- **Passed:** 3
- **Failed:** 0
- **Warnings:** 5

## Performance Analysis

### Slowest Test
- **test_deepseek_api** (6.37s) - 66.4% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest llm -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_deepseek_api` (takes 6.37s)
