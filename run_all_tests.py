"""
Comprehensive test runner for all chatbot service tests.

This script runs all test cases systematically and provides a summary report.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_test(test_path, description, timeout=300):
    """Run a test and return success status."""
    print(f"\n{'='*80}")
    print(f"Running: {description}")
    print(f"File: {test_path}")
    print(f"{'='*80}")
    
    try:
        test_file = project_root / test_path
        if not test_file.exists():
            print(f"[SKIPPED]: File not found")
            return None
        
        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        
        # Print output
        if result.stdout:
            # Print last 20 lines of output
            lines = result.stdout.split('\n')
            for line in lines[-20:]:
                if line.strip():
                    print(line)
        
        # Check if test passed (exit code 0)
        if result.returncode == 0:
            print("\n[PASSED]")
            return True
        else:
            print("\n[FAILED]")
            # Print errors
            if result.stderr:
                print("\nErrors:")
                error_lines = result.stderr.split('\n')
                for line in error_lines[-10:]:
                    if line.strip():
                        print(f"  {line}")
            return False
    except subprocess.TimeoutExpired:
        print(f"\n[TIMEOUT] (exceeded {timeout}s)")
        return False
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        return False

def main():
    """Run all tests and summarize results."""
    print("="*80)
    print("CHATBOT SERVICE - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define all tests organized by category
    test_suite = {
        "Unit Tests": [
            ("tests/unit/test_logger.py", "Logger Unit Test", 30),
            ("tests/unit/test_input.py", "Input Validation Test", 30),
        ],
        "LLM Provider Tests": [
            ("tests/integration/llm/test_openai_provider.py", "OpenAI Provider Connectivity", 120),
            ("tests/integration/llm/test_gemini_provider.py", "Gemini Provider Connectivity", 120),
            ("tests/integration/llm/test_deepseek_provider.py", "DeepSeek Provider Connectivity", 120),
        ],
        "Agent Integration Tests": [
            ("tests/integration/agent/test_agent_basic.py", "Basic Agent Functionality", 180),
            ("tests/integration/agent/test_deepseek_chatbot.py", "DeepSeek Chatbot Integration", 180),
        ],
        "RAG Service Tests": [
            ("tests/integration/rag/test_rag_simple.py", "RAG Simple Test", 60),
            ("tests/integration/rag/test_rag_service.py", "RAG Service Test", 120),
            ("tests/integration/rag/test_rag_context.py", "RAG Context Test", 120),
            ("tests/integration/rag/test_rag_context_safe.py", "RAG Context Safe Test", 120),
        ],
        "Memory Tests": [
            ("tests/integration/memory/test_memory_manager.py", "Memory Manager Test", 120),
            ("tests/integration/memory/test_persistence.py", "Memory Persistence Test", 120),
        ],
        "MCP Integration Tests": [
            ("tests/integration/mcp/test_mcp_connection.py", "MCP Connection Test", 60),
            ("tests/integration/mcp/test_mcp_enabled.py", "MCP Enabled Test", 60),
            ("tests/integration/mcp/test_mcp_jira_direct.py", "MCP Jira Direct Test", 180),
            ("tests/integration/mcp/test_mcp_jira_creation.py", "MCP Jira Creation Test", 180),
            ("tests/integration/mcp/test_confluence_mcp_simple.py", "Confluence MCP Simple Test", 120),
        ],
    }
    
    results = []
    category_results = {}
    
    # Run tests by category
    for category, tests in test_suite.items():
        print(f"\n\n{'#'*80}")
        print(f"# {category}")
        print(f"{'#'*80}")
        
        category_passed = 0
        category_failed = 0
        category_skipped = 0
        
        for test_path, description, timeout in tests:
            result = run_test(test_path, description, timeout)
            results.append((category, description, result))
            
            if result is True:
                category_passed += 1
            elif result is False:
                category_failed += 1
            else:
                category_skipped += 1
        
        category_results[category] = {
            'passed': category_passed,
            'failed': category_failed,
            'skipped': category_skipped,
            'total': len(tests)
        }
    
    # Summary Report
    print("\n\n" + "="*80)
    print("TEST SUMMARY REPORT")
    print("="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    total_passed = sum(1 for _, _, result in results if result is True)
    total_failed = sum(1 for _, _, result in results if result is False)
    total_skipped = sum(1 for _, _, result in results if result is None)
    total_tests = len(results)
    
    # Category breakdown
    print("Results by Category:")
    print("-" * 80)
    for category, stats in category_results.items():
        print(f"\n{category}:")
        print(f"  Total: {stats['total']}")
        print(f"  [PASSED]: {stats['passed']}")
        print(f"  [FAILED]: {stats['failed']}")
        print(f"  [SKIPPED]: {stats['skipped']}")
        if stats['total'] > 0:
            success_rate = (stats['passed'] / stats['total']) * 100
            print(f"  Success Rate: {success_rate:.1f}%")
    
    # Overall summary
    print("\n" + "-" * 80)
    print("Overall Summary:")
    print(f"  Total Tests: {total_tests}")
    print(f"  [PASSED]: {total_passed}")
    print(f"  [FAILED]: {total_failed}")
    print(f"  [SKIPPED]: {total_skipped}")
    
    if total_tests > 0:
        overall_success_rate = (total_passed / total_tests) * 100
        print(f"  Overall Success Rate: {overall_success_rate:.1f}%")
    
    # Detailed results
    print("\n" + "-" * 80)
    print("Detailed Results:")
    print("-" * 80)
    for category, description, result in results:
        if result is True:
            status = "[PASSED]"
        elif result is False:
            status = "[FAILED]"
        else:
            status = "[SKIPPED]"
        print(f"  [{category}] {status}: {description}")
    
    print("\n" + "="*80)
    
    # Exit code
    if total_failed == 0:
        print("[SUCCESS] ALL TESTS PASSED!")
        return 0
    else:
        print(f"[FAILED] {total_failed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())

