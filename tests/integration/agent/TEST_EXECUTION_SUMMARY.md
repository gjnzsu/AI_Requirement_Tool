# AGENT Tests - Execution Time Summary

**Test Run Date:** 2025-12-16 22:38:50  
**Total Execution Time:** 56.65 seconds  
**Total Tests:** 2  
**Passed:** 2 [PASS]  
**Failed:** 0  
**Warnings:** 3 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_agent` | **46.18s** | [PASS] PASSED | |
| `test_deepseek_chatbot` | **10.47s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 56.65 seconds
- **Average Time:** 28.32 seconds
- **Slowest Test:** `test_agent` (46.18s)
- **Fastest Test:** `test_deepseek_chatbot` (10.47s)

### Test Results
- **Passed:** 2
- **Failed:** 0
- **Warnings:** 3

## Performance Analysis

### Slowest Test
- **test_agent** (46.18s) - 81.5% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest agent -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_agent` (takes 46.18s)
