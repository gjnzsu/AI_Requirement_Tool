# AGENT Tests - Execution Time Summary

**Test Run Date:** 2025-12-12 15:22:18  
**Total Execution Time:** 0.00 seconds  
**Total Tests:** 2  
**Passed:** 2 [PASS]  
**Failed:** 0  
**Warnings:** 3 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_agent` | **73.23s** | [PASS] PASSED | |
| `test_deepseek_chatbot` | **13.04s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 0.00 seconds
- **Average Time:** 43.14 seconds
- **Slowest Test:** `test_agent` (73.23s)
- **Fastest Test:** `test_deepseek_chatbot` (13.04s)

### Test Results
- **Passed:** 2
- **Failed:** 0
- **Warnings:** 3

## Performance Analysis

### Slowest Test
- **test_agent** (73.23s) - 0.0% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest agent -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_agent` (takes 73.23s)
