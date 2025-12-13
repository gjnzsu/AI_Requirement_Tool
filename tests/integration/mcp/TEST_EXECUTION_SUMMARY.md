# MCP Tests - Execution Time Summary

**Test Run Date:** 2025-12-13 12:55:31  
**Execution Mode:** Parallel (4 workers)
**Total Execution Time:** 167.93 seconds  
**Total Tests:** 26  
**Passed:** 24 [PASS]  
**Failed:** 2  
**Warnings:** 14 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_mcp_jira_direct` | **34.48s** | [PASS] PASSED | |
| `test_0_health_check_confluence_mcp_server` | **18.76s** | [PASS] PASSED | |
| `test_confluence_mcp_server` | **16.05s** | [PASS] PASSED | |
| `test_12_contentformat_enum_contract` | **11.07s** | [PASS] PASSED | |
| `test_mcp_integration` | **10.68s** | [PASS] PASSED | |
| `test_full_mcp_integration` | **10.63s** | [PASS] PASSED | |
| `test_mcp_fix` | **9.93s** | [PASS] PASSED | |
| `test_mcp_integration` | **9.81s** | [PASS] PASSED | |
| `test_rovo_mcp_server` | **8.77s** | [PASS] PASSED | |
| `test_9_cloudid_handling_for_rovo_tools` | **6.69s** | [PASS] PASSED | |
| `test_10_end_to_end_confluence_integration` | **5.11s** | [PASS] PASSED | |
| `test_6_jira_creation_workflow_langgraph` | **4.04s** | [PASS] PASSED | |
| `test_2_retrieve_confluence_page_info_via_mcp` | **3.60s** | [PASS] PASSED | |
| `test_3_non_jira_flows_dont_trigger_confluence_mcp` | **3.30s** | [PASS] PASSED | |
| `test_13_schema_enum_extraction_contract` | **2.89s** | [PASS] PASSED | |
| `test_8_jira_creation_timeout_handling` | **2.82s** | [PASS] PASSED | |
| `test_custom_jira_mcp` | **2.75s** | [PASS] PASSED | |
| `test_4_timeout_fallback_to_direct_api` | **2.73s** | [PASS] PASSED | |
| `test_mcp_enabled` | **2.33s** | [PASS] PASSED | |
| `test_5_confluence_tooling_queries_go_to_general_chat` | **2.26s** | [PASS] PASSED | |
| `test_7_basic_model_call_works` | **1.80s** | [PASS] PASSED | |
| `test_custom_tools` | **1.63s** | [PASS] PASSED | |
| `test_11_tool_invoke_contract_validation` | **1.49s** | [PASS] PASSED | |
| `test_1_mcp_protocol_called_and_logged` | **1.38s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 167.93 seconds
- **Average Time:** 7.29 seconds
- **Slowest Test:** `test_mcp_jira_direct` (34.48s)
- **Fastest Test:** `test_1_mcp_protocol_called_and_logged` (1.38s)

### Test Results
- **Passed:** 24
- **Failed:** 2
- **Warnings:** 14
- **Parallel Workers:** 4

## Performance Analysis

### Slowest Test
- **test_mcp_jira_direct** (34.48s) - 20.5% of total execution time
  - May include network latency, API calls, or complex operations


## Command Used

```bash
python -m pytest mcp -v --durations=0 --tb=short -n=4
```

## Recommendations

- Consider optimizing `test_mcp_jira_direct` (takes 34.48s)
- 2 test(s) failed - review and fix
- 14 warnings detected - review for potential issues
