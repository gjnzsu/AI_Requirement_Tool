"""
Test runner script with execution time tracking and report generation.

This script runs tests one category at a time, captures execution times,
and generates detailed execution time reports for each category.

Usage:
    python scripts/run_tests_with_timing.py                    # Run all test categories
    python scripts/run_tests_with_timing.py --category unit   # Run specific category
"""

import sys
import subprocess
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestResult:
    """Store test execution results."""
    def __init__(self, name: str, duration: float, status: str = "PASSED"):
        self.name = name
        self.duration = duration
        self.status = status


def parse_pytest_output(output: str) -> Tuple[List[TestResult], Dict]:
    """Parse pytest output to extract test results and timing information."""
    results = []
    summary = {
        "total_time": 0.0,
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
    
    # Extract total execution time
    total_match = re.search(r'(\d+\.\d+)s\s+total', output)
    if total_match:
        summary["total_time"] = float(total_match.group(1))
    
    # Extract passed/failed counts
    passed_match = re.search(r'(\d+)\s+passed', output)
    if passed_match:
        summary["passed"] = int(passed_match.group(1))
    
    failed_match = re.search(r'(\d+)\s+failed', output)
    if failed_match:
        summary["failed"] = int(failed_match.group(1))
    
    warnings_match = re.search(r'(\d+)\s+warnings?', output)
    if warnings_match:
        summary["warnings"] = int(warnings_match.group(1))
    
    # Extract individual test durations from "slowest durations" section
    durations_section = False
    for line in output.split('\n'):
        if 'slowest durations' in line.lower():
            durations_section = True
            continue
        
        if durations_section:
            # Match lines like: "7.88s call     tests/integration/llm/test_deepseek_provider.py::test_deepseek_api"
            match = re.match(r'\s*(\d+\.\d+)s\s+call\s+(.+)', line)
            if match:
                duration = float(match.group(1))
                test_name = match.group(2).strip()
                # Extract just the test function name
                test_func = test_name.split('::')[-1] if '::' in test_name else test_name
                results.append(TestResult(test_func, duration))
            elif line.strip() and not line.startswith('='):
                # End of durations section
                break
    
    # If no durations found, try to extract from test results
    if not results:
        for line in output.split('\n'):
            # Match lines like: "tests/unit/test_input.py::test_input_output PASSED [ 50%]"
            match = re.match(r'.+::(.+?)\s+(PASSED|FAILED)', line)
            if match:
                test_func = match.group(1)
                status = match.group(2)
                # Try to find duration in next lines or use 0.01 as default
                results.append(TestResult(test_func, 0.01, status))
    
    return results, summary


def run_tests(category_path: str, category_name: str) -> Tuple[List[TestResult], Dict]:
    """Run tests for a specific category and return results."""
    print(f"\n{'='*70}")
    print(f"Running {category_name} tests...")
    print(f"{'='*70}")
    
    cmd = [
        sys.executable, "-m", "pytest",
        category_path,
        "-v",
        "--durations=0",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per category
        )
        
        output = result.stdout + result.stderr
        print(output)
        
        test_results, summary = parse_pytest_output(output)
        summary["exit_code"] = result.returncode
        
        return test_results, summary
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Tests for {category_name} timed out after 5 minutes")
        return [], {"total_time": 300.0, "passed": 0, "failed": 0, "warnings": 0, "exit_code": 1, "timeout": True}
    except Exception as e:
        print(f"ERROR running tests for {category_name}: {e}")
        return [], {"total_time": 0.0, "passed": 0, "failed": 0, "warnings": 0, "exit_code": 1, "error": str(e)}


def generate_report(category_name: str, test_results: List[TestResult], summary: Dict, output_path: Path):
    """Generate markdown report for a test category."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Sort results by duration (slowest first)
    sorted_results = sorted(test_results, key=lambda x: x.duration, reverse=True)
    
    # Calculate statistics
    total_tests = len(test_results)
    if total_tests > 0:
        avg_time = sum(r.duration for r in test_results) / total_tests
        slowest = sorted_results[0] if sorted_results else None
        fastest = sorted_results[-1] if sorted_results else None
    else:
        avg_time = 0.0
        slowest = None
        fastest = None
    
    # Handle timeout/failed tests
    if summary.get('timeout') or summary.get('exit_code', 0) != 0:
        total_tests = max(total_tests, summary.get('passed', 0) + summary.get('failed', 0))
    
    report = f"""# {category_name.upper()} Tests - Execution Time Summary

**Test Run Date:** {timestamp}  
**Total Execution Time:** {summary.get('total_time', 0):.2f} seconds  
**Total Tests:** {total_tests}  
**Passed:** {summary.get('passed', 0)} [PASS]  
**Failed:** {summary.get('failed', 0)}  
**Warnings:** {summary.get('warnings', 0)} (non-critical)

## Test Case Execution Times

| Test Case | Execution Time | Status | Notes |
|-----------|----------------|--------|-------|
"""
    
    for result in sorted_results:
        status_icon = "[PASS]" if result.status == "PASSED" else "[FAIL]"
        report += f"| `{result.name}` | **{result.duration:.2f}s** | {status_icon} {result.status} | |\n"
    
    report += f"""
## Performance Statistics

### Execution Times
- **Total Time:** {summary.get('total_time', 0):.2f} seconds
- **Average Time:** {avg_time:.2f} seconds
"""
    
    if slowest:
        report += f"- **Slowest Test:** `{slowest.name}` ({slowest.duration:.2f}s)\n"
    if fastest:
        report += f"- **Fastest Test:** `{fastest.name}` ({fastest.duration:.2f}s)\n"
    
    report += f"""
### Test Results
- **Passed:** {summary.get('passed', 0)}
- **Failed:** {summary.get('failed', 0)}
- **Warnings:** {summary.get('warnings', 0)}

## Performance Analysis

"""
    
    if slowest:
        percentage = (slowest.duration / summary.get('total_time', 1)) * 100 if summary.get('total_time', 0) > 0 else 0
        report += f"""### Slowest Test
- **{slowest.name}** ({slowest.duration:.2f}s) - {percentage:.1f}% of total execution time
  - May include network latency, API calls, or complex operations

"""
    
    if fastest and fastest.duration < 0.1:
        report += f"""### Fastest Test
- **{fastest.name}** ({fastest.duration:.2f}s) - Instant execution
  - Likely using mocked responses or simple operations

"""
    
    if summary.get('timeout'):
        report += "\n[WARN] **Warning:** Tests timed out after 5 minutes\n"
    if summary.get('error'):
        report += f"\n[ERROR] **Error:** {summary.get('error')}\n"
    
    report += f"""
## Command Used

```bash
python -m pytest {category_name} -v --durations=0 --tb=short
```

## Recommendations

"""
    
    if slowest and slowest.duration > 5.0:
        report += f"- Consider optimizing `{slowest.name}` (takes {slowest.duration:.2f}s)\n"
    if summary.get('failed', 0) > 0:
        report += f"- {summary.get('failed', 0)} test(s) failed - review and fix\n"
    if summary.get('warnings', 0) > 5:
        report += f"- {summary.get('warnings', 0)} warnings detected - review for potential issues\n"
    
    if not slowest or slowest.duration < 1.0:
        report += "- All tests execute quickly [OK]\n"
    
    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding='utf-8')
    print(f"\n[OK] Report generated: {output_path}")


def main():
    """Main test runner."""
    # Define test categories
    categories = {
        "unit": {
            "path": "tests/unit/",
            "report_path": "tests/unit/TEST_EXECUTION_SUMMARY.md"
        },
        "llm": {
            "path": "tests/integration/llm/",
            "report_path": "tests/integration/llm/TEST_EXECUTION_SUMMARY.md"
        },
        "memory": {
            "path": "tests/integration/memory/",
            "report_path": "tests/integration/memory/TEST_EXECUTION_SUMMARY.md"
        },
        "rag": {
            "path": "tests/integration/rag/",
            "report_path": "tests/integration/rag/TEST_EXECUTION_SUMMARY.md"
        },
        "agent": {
            "path": "tests/integration/agent/",
            "report_path": "tests/integration/agent/TEST_EXECUTION_SUMMARY.md"
        },
        "api": {
            "path": "tests/integration/api/",
            "report_path": "tests/integration/api/TEST_EXECUTION_SUMMARY.md"
        },
        "mcp": {
            "path": "tests/integration/mcp/",
            "report_path": "tests/integration/mcp/TEST_EXECUTION_SUMMARY.md"
        }
    }
    
    # Check if specific category requested
    if len(sys.argv) > 1 and sys.argv[1] == "--category":
        if len(sys.argv) > 2:
            category_name = sys.argv[2].lower()
            if category_name in categories:
                categories = {category_name: categories[category_name]}
            else:
                print(f"Unknown category: {category_name}")
                print(f"Available categories: {', '.join(categories.keys())}")
                return 1
        else:
            print("Usage: python scripts/run_tests_with_timing.py --category <category_name>")
            return 1
    
    # Run tests for each category
    all_results = {}
    
    for category_name, config in categories.items():
        test_results, summary = run_tests(config["path"], category_name)
        report_path = project_root / config["report_path"]
        generate_report(category_name, test_results, summary, report_path)
        all_results[category_name] = {
            "results": test_results,
            "summary": summary,
            "report_path": config["report_path"]
        }
    
    # Generate master summary
    generate_master_summary(all_results)
    
    return 0


def generate_master_summary(all_results: Dict):
    """Generate master summary report aggregating all categories."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    total_time = sum(r["summary"].get("total_time", 0) for r in all_results.values())
    total_passed = sum(r["summary"].get("passed", 0) for r in all_results.values())
    total_failed = sum(r["summary"].get("failed", 0) for r in all_results.values())
    total_tests = total_passed + total_failed
    if total_tests == 0:
        total_tests = sum(len(r["results"]) for r in all_results.values())
    
    # Collect all slowest tests
    all_slowest = []
    for category_name, data in all_results.items():
        results = data["results"]
        if results:
            sorted_results = sorted(results, key=lambda x: x.duration, reverse=True)
            for result in sorted_results[:3]:  # Top 3 slowest per category
                all_slowest.append((category_name, result))
    
    # Sort by duration
    all_slowest.sort(key=lambda x: x[1].duration, reverse=True)
    
    report = f"""# Test Execution Master Summary

**Generated:** {timestamp}  
**Total Execution Time:** {total_time:.2f} seconds  
**Total Tests:** {total_tests}  
**Passed:** {total_passed} [PASS]  
**Failed:** {total_failed}  
**Categories:** {len(all_results)}

## Summary by Category

| Category | Tests | Passed | Failed | Execution Time | Avg Time/Test |
|----------|-------|--------|--------|----------------|---------------|
"""
    
    for category_name, data in sorted(all_results.items()):
        summary = data["summary"]
        results = data["results"]
        num_tests = len(results)
        exec_time = summary.get("total_time", 0)
        avg_time = exec_time / num_tests if num_tests > 0 else 0
        
        report += f"| **{category_name.upper()}** | {num_tests} | {summary.get('passed', 0)} | {summary.get('failed', 0)} | {exec_time:.2f}s | {avg_time:.2f}s |\n"
    
    report += f"""
## Slowest Tests Across All Categories

| Rank | Test Case | Category | Execution Time | Percentage |
|------|-----------|----------|----------------|------------|
"""
    
    for idx, (category, result) in enumerate(all_slowest[:10], 1):  # Top 10 slowest
        percentage = (result.duration / total_time * 100) if total_time > 0 else 0
        report += f"| {idx} | `{result.name}` | {category} | **{result.duration:.2f}s** | {percentage:.1f}% |\n"
    
    report += f"""
## Overall Statistics

- **Total Execution Time:** {total_time:.2f} seconds ({total_time/60:.1f} minutes)
- **Average Time per Test:** {(total_time/total_tests if total_tests > 0 else 0):.2f}s ({total_tests} tests)
- **Success Rate:** {(total_passed/total_tests*100 if total_tests > 0 else 0):.1f}% ({total_passed}/{total_tests})
- **Categories Tested:** {len(all_results)}

## Recommendations

"""
    
    if total_failed > 0:
        report += f"- [WARN] {total_failed} test(s) failed - review and fix\n"
    
    if all_slowest:
        slowest = all_slowest[0]
        if slowest[1].duration > 10.0:
            report += f"- [SLOW] Slowest test: `{slowest[1].name}` ({slowest[1].duration:.2f}s) - consider optimization\n"
    
    if total_time > 300:  # 5 minutes
        report += f"- [TIME] Total execution time is {total_time/60:.1f} minutes - consider parallel execution\n"
    
    report += """
## Category Reports

For detailed reports, see:
"""
    
    for category_name, data in sorted(all_results.items()):
        report_path = data["report_path"]
        report += f"- **[{category_name.upper()}]({report_path})**\n"
    
    # Write master summary
    master_path = project_root / "tests/TEST_EXECUTION_MASTER_SUMMARY.md"
    master_path.write_text(report, encoding='utf-8')
    print(f"\n[OK] Master summary generated: {master_path}")


if __name__ == "__main__":
    sys.exit(main())

