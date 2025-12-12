# MEMORY Tests - Execution Time Summary

**Test Run Date:** 2025-12-12 15:18:45  
**Total Execution Time:** 0.00 seconds  
**Total Tests:** 2  
**Passed:** 2 [PASS]  
**Failed:** 0  
**Warnings:** 4 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_chatbot_integration` | **21.13s** | [PASS] PASSED | |
| `test_memory_manager` | **0.07s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 0.00 seconds
- **Average Time:** 10.60 seconds
- **Slowest Test:** `test_chatbot_integration` (21.13s)
- **Fastest Test:** `test_memory_manager` (0.07s)

### Test Results
- **Passed:** 2
- **Failed:** 0
- **Warnings:** 4

## Performance Analysis

### Slowest Test
- **test_chatbot_integration** (21.13s) - 0.0% of total execution time
  - May include network latency, API calls, or complex operations

### Fastest Test
- **test_memory_manager** (0.07s) - Instant execution
  - Likely using mocked responses or simple operations


## Command Used

```bash
python -m pytest memory -v --durations=0 --tb=short
```

## Recommendations

- Consider optimizing `test_chatbot_integration` (takes 21.13s)
