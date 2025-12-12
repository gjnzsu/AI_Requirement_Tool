# LLM Tests - Execution Time Summary

**Test Run Date:** 2025-12-12 15:18:02  
**Total Execution Time:** 0.00 seconds  
**Total Tests:** 2  
**Passed:** 3 [PASS]  
**Failed:** 0  
**Warnings:** 5 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_deepseek_api` | **6.13s** | [PASS] PASSED | |
| `test_openai_api` | **3.04s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 0.00 seconds
- **Average Time:** 4.58 seconds
- **Slowest Test:** `test_deepseek_api` (6.13s)
- **Fastest Test:** `test_openai_api` (3.04s)

### Test Results
- **Passed:** 3
- **Failed:** 0
- **Warnings:** 5

## Performance Analysis

### Slowest Test
- **test_deepseek_api** (6.13s) - 0.0% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest llm -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_deepseek_api` (takes 6.13s)
