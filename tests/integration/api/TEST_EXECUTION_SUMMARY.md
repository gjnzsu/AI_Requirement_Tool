# API Tests - Execution Time Summary

**Test Run Date:** 2025-12-12 15:22:42  
**Total Execution Time:** 0.00 seconds  
**Total Tests:** 37  
**Passed:** 34 [PASS]  
**Failed:** 3  
**Warnings:** 2 (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
| `test_chat_success` | **0.01s** | [PASS] PASSED | |
| `test_chat_with_conversation_id` | **0.01s** | [PASS] PASSED | |
| `test_chat_provider_switching_openai` | **0.01s** | [FAIL] FAILED | |
| `test_chat_provider_switching_gemini` | **0.01s** | [PASS] PASSED | |
| `test_chat_provider_switching_deepseek` | **0.01s** | [PASS] PASSED | |
| `test_chat_invalid_model` | **0.01s** | [PASS] PASSED | |
| `test_chat_empty_message` | **0.01s** | [PASS] PASSED | |
| `test_chat_missing_message` | **0.01s** | [PASS] PASSED | |
| `test_chat_memory_persistence` | **0.01s** | [PASS] PASSED | |
| `test_chat_llm_failure` | **0.01s** | [PASS] PASSED | |
| `test_chat_provider_switch_failure` | **0.01s** | [FAIL] FAILED | |
| `test_chat_conversation_title_update` | **0.01s** | [PASS] PASSED | |
| `test_list_conversations_empty` | **0.01s** | [PASS] PASSED | |
| `test_list_conversations_with_data` | **0.01s** | [PASS] PASSED | |
| `test_get_conversation_exists` | **0.01s** | [PASS] PASSED | |
| `test_get_conversation_not_found` | **0.01s** | [PASS] PASSED | |
| `test_delete_conversation_exists` | **0.01s** | [PASS] PASSED | |
| `test_delete_conversation_not_found` | **0.01s** | [PASS] PASSED | |
| `test_clear_all_conversations` | **0.01s** | [PASS] PASSED | |
| `test_update_conversation_title` | **0.01s** | [PASS] PASSED | |
| `test_update_conversation_title_empty` | **0.01s** | [PASS] PASSED | |
| `test_update_conversation_title_not_found` | **0.01s** | [PASS] PASSED | |
| `test_create_new_chat` | **0.01s** | [PASS] PASSED | |
| `test_conversation_persistence_across_calls` | **0.01s** | [PASS] PASSED | |
| `test_get_current_model` | **0.01s** | [PASS] PASSED | |
| `test_get_current_model_gemini` | **0.01s** | [PASS] PASSED | |
| `test_get_current_model_deepseek` | **0.01s** | [PASS] PASSED | |
| `test_get_current_model_chatbot_creation_error` | **0.01s** | [PASS] PASSED | |
| `test_model_switching_persistence` | **0.01s** | [PASS] PASSED | |
| `test_search_with_query` | **0.01s** | [PASS] PASSED | |
| `test_search_with_limit` | **0.01s** | [PASS] PASSED | |
| `test_search_no_results` | **0.01s** | [PASS] PASSED | |
| `test_search_missing_query` | **0.01s** | [PASS] PASSED | |
| `test_search_empty_query` | **0.01s** | [PASS] PASSED | |
| `test_search_integration_with_memory_manager` | **0.01s** | [PASS] PASSED | |
| `test_search_limit_validation` | **0.01s** | [FAIL] FAILED | |
| `test_search_special_characters` | **0.01s** | [PASS] PASSED | |

## Performance Statistics

### Execution Times
- **Total Time:** 0.00 seconds
- **Average Time:** 0.01 seconds
- **Slowest Test:** `test_chat_success` (0.01s)
- **Fastest Test:** `test_search_special_characters` (0.01s)

### Test Results
- **Passed:** 34
- **Failed:** 3
- **Warnings:** 2

## Performance Analysis

### Slowest Test
- **test_chat_success** (0.01s) - 0.0% of total execution time
  - May include network latency, API calls, or complex operations

### Fastest Test
- **test_search_special_characters** (0.01s) - Instant execution
  - Likely using mocked responses or simple operations


## Command Used

```bash
python -m pytest api -v --durations=0 --tb=short
```

## Recommendations

- 3 test(s) failed - review and fix
- All tests execute quickly [OK]
