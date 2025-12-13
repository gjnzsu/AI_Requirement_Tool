"""
Parallel test runner script with execution time tracking and report generation.

This script runs tests in parallel at two levels:
1. Test categories run in parallel (unit, llm, memory, etc.)
2. Tests within each category run in parallel using pytest-xdist

Usage:
    python scripts/run_tests_with_timing_parallel.py                    # Run all categories in parallel
    python scripts/run_tests_with_timing_parallel.py --category unit    # Run specific category with parallel tests
    python scripts/run_tests_with_timing_parallel.py --workers 4       # Use 4 workers per category
    python scripts/run_tests_with_timing_parallel.py --no-category-parallel  # Disable category-level parallelism
"""

import sys
import subprocess
import re
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Set UTF-8 encoding for Windows compatibility
os.environ['PYTHONIOENCODING'] = 'utf-8'

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
    
    # Extract summary line: "X passed, Y failed, Z warnings in N.NNs"
    # Try multiple patterns to handle different pytest output formats (including pytest-xdist)
    summary_match = re.search(r'=\s+(\d+)\s+passed(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+warnings?)?\s+in\s+(\d+\.\d+)s\s+=', output)
    if summary_match:
        summary["passed"] = int(summary_match.group(1))
        summary["failed"] = int(summary_match.group(2)) if summary_match.group(2) else 0
        summary["warnings"] = int(summary_match.group(3)) if summary_match.group(3) else 0
        summary["total_time"] = float(summary_match.group(4))
    else:
        # Fallback: try separate patterns (works for pytest-xdist output)
        passed_match = re.search(r'(\d+)\s+passed', output)
        if passed_match:
            summary["passed"] = int(passed_match.group(1))
        
        failed_match = re.search(r'(\d+)\s+failed', output)
        if failed_match:
            summary["failed"] = int(failed_match.group(1))
        
        warnings_match = re.search(r'(\d+)\s+warnings?', output)
        if warnings_match:
            summary["warnings"] = int(warnings_match.group(1))
        
        # Try to extract time from summary line (pytest-xdist format)
        time_match = re.search(r'in\s+(\d+\.\d+)s', output)
        if time_match:
            summary["total_time"] = float(time_match.group(1))
    
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
                # Determine status from test name or output
                status = "PASSED"
                if "FAILED" in line or "ERROR" in line:
                    status = "FAILED"
                results.append(TestResult(test_func, duration, status))
            elif line.strip() and not line.startswith('='):
                # End of durations section
                break
    
    # If no durations found, try to extract from test results
    if not results:
        for line in output.split('\n'):
            # Match lines like: "tests/unit/test_input.py::test_input_output PASSED [ 50%]"
            match = re.match(r'.+::(.+?)\s+(PASSED|FAILED|ERROR|SKIPPED)', line)
            if match:
                test_func = match.group(1)
                status = match.group(2)
                # Try to find duration in next lines or use 0.01 as default
                results.append(TestResult(test_func, 0.01, status))
    
    # If total_time wasn't found in summary, calculate from individual test durations
    if summary["total_time"] == 0.0 and results:
        summary["total_time"] = sum(r.duration for r in results)
    
    return results, summary


def run_tests_parallel(category_path: str, category_name: str, workers: int = None) -> Tuple[List[TestResult], Dict]:
    """Run tests for a specific category in parallel and return results."""
    print(f"\n{'='*70}")
    print(f"Running {category_name} tests (parallel)...")
    print(f"{'='*70}")
    
    # Determine number of workers (auto-detect CPU count if not specified)
    if workers is None:
        import os
        workers = os.cpu_count() or 2
        # Limit to reasonable number for test execution
        workers = min(workers, 4)
    
    cmd = [
        sys.executable, "-m", "pytest",
        category_path,
        "-v",
        "--durations=0",
        "--tb=short",
        f"-n={workers}",  # pytest-xdist parallel execution
        "--dist=worksteal"  # Better load balancing
    ]
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace encoding errors instead of failing
            timeout=600  # 10 minute timeout per category
        )
        elapsed_time = time.time() - start_time
        
        output = (result.stdout or '') + (result.stderr or '')
        print(output)
        
        test_results, summary = parse_pytest_output(output)
        summary["exit_code"] = result.returncode
        summary["workers"] = workers
        summary["elapsed_time"] = elapsed_time
        
        return test_results, summary
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Tests for {category_name} timed out after 10 minutes")
        return [], {"total_time": 600.0, "passed": 0, "failed": 0, "warnings": 0, "exit_code": 1, "timeout": True, "workers": workers}
    except Exception as e:
        print(f"ERROR running tests for {category_name}: {e}")
        return [], {"total_time": 0.0, "passed": 0, "failed": 0, "warnings": 0, "exit_code": 1, "error": str(e), "workers": workers}


def run_tests_sequential(category_path: str, category_name: str) -> Tuple[List[TestResult], Dict]:
    """Run tests for a specific category sequentially (fallback if pytest-xdist not available)."""
    print(f"\n{'='*70}")
    print(f"Running {category_name} tests (sequential)...")
    print(f"{'='*70}")
    
    cmd = [
        sys.executable, "-m", "pytest",
        category_path,
        "-v",
        "--durations=0",
        "--tb=short"
    ]
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace encoding errors instead of failing
            timeout=300  # 5 minute timeout per category
        )
        elapsed_time = time.time() - start_time
        
        output = (result.stdout or '') + (result.stderr or '')
        print(output)
        
        test_results, summary = parse_pytest_output(output)
        summary["exit_code"] = result.returncode
        summary["elapsed_time"] = elapsed_time
        
        return test_results, summary
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Tests for {category_name} timed out after 5 minutes")
        return [], {"total_time": 300.0, "passed": 0, "failed": 0, "warnings": 0, "exit_code": 1, "timeout": True}
    except Exception as e:
        print(f"ERROR running tests for {category_name}: {e}")
        return [], {"total_time": 0.0, "passed": 0, "failed": 0, "warnings": 0, "exit_code": 1, "error": str(e)}


def check_pytest_xdist():
    """Check if pytest-xdist is installed."""
    try:
        import xdist
        return True
    except ImportError:
        return False


def generate_report(category_name: str, test_results: List[TestResult], summary: Dict, output_path: Path):
    """Generate markdown report for a test category."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Sort results by duration (slowest first)
    sorted_results = sorted(test_results, key=lambda x: x.duration, reverse=True)
    
    # Calculate statistics
    # Use summary counts (passed + failed) as authoritative, fallback to results length
    total_tests_from_summary = summary.get('passed', 0) + summary.get('failed', 0)
    total_tests = max(len(test_results), total_tests_from_summary) if total_tests_from_summary > 0 else len(test_results)
    
    if test_results:
        avg_time = sum(r.duration for r in test_results) / len(test_results)
        slowest = sorted_results[0] if sorted_results else None
        fastest = sorted_results[-1] if sorted_results else None
    else:
        avg_time = 0.0
        slowest = None
        fastest = None
    
    # Use total_time from summary if available, otherwise calculate from results
    total_time = summary.get('total_time', 0.0)
    if total_time == 0.0 and test_results:
        total_time = sum(r.duration for r in test_results)
    
    # Get execution mode info
    workers = summary.get('workers', 1)
    execution_mode = f"Parallel ({workers} workers)" if workers > 1 else "Sequential"
    
    report = f"""# {category_name.upper()} Tests - Execution Time Summary

**Test Run Date:** {timestamp}  
**Execution Mode:** {execution_mode}
**Total Execution Time:** {total_time:.2f} seconds  
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
- **Total Time:** {total_time:.2f} seconds
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
"""
    
    if workers > 1:
        report += f"- **Parallel Workers:** {workers}\n"
    
    report += f"""
## Performance Analysis

"""
    
    if slowest:
        percentage = (slowest.duration / total_time * 100) if total_time > 0 else 0
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
        report += "\n[WARN] **Warning:** Tests timed out\n"
    if summary.get('error'):
        report += f"\n[ERROR] **Error:** {summary.get('error')}\n"
    
    report += f"""
## Command Used

```bash
python -m pytest {category_name} -v --durations=0 --tb=short{" -n=" + str(workers) if workers > 1 else ""}
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


def run_category_tests(category_name: str, config: Dict, workers: int = None, use_parallel: bool = True) -> Dict:
    """Run tests for a single category and return results."""
    category_path = config["path"]
    report_path = project_root / config["report_path"]
    
    # Check if pytest-xdist is available for parallel execution
    if use_parallel and check_pytest_xdist():
        test_results, summary = run_tests_parallel(category_path, category_name, workers)
    else:
        if use_parallel and not check_pytest_xdist():
            print(f"[WARN] pytest-xdist not installed. Install with: pip install pytest-xdist")
            print(f"[INFO] Running {category_name} tests sequentially...")
        test_results, summary = run_tests_sequential(category_path, category_name)
    
    generate_report(category_name, test_results, summary, report_path)
    
    return {
        "results": test_results,
        "summary": summary,
        "report_path": config["report_path"]
    }


def generate_master_summary(all_results: Dict, wall_clock_time: float = None):
    """Generate master summary report aggregating all categories.
    
    Args:
        all_results: Dictionary of category results
        wall_clock_time: Actual wall-clock time elapsed (for parallel execution)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate totals from summaries, with fallback to results
    total_time = 0.0  # Sum of all test execution times
    total_passed = 0
    total_failed = 0
    
    for r in all_results.values():
        summary = r["summary"]
        results = r["results"]
        
        # Get execution time from summary, fallback to sum of result durations
        exec_time = summary.get("total_time", 0)
        if exec_time == 0.0 and results:
            exec_time = sum(result.duration for result in results)
        total_time += exec_time
        
        # Get counts from summary
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        
        # If summary doesn't have counts, try to infer from results
        if passed == 0 and failed == 0 and results:
            # Count passed/failed from result status
            passed = sum(1 for result in results if result.status == "PASSED")
            failed = sum(1 for result in results if result.status == "FAILED")
        
        total_passed += passed
        total_failed += failed
    
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
    
    # Check if parallel execution was used
    parallel_used = any(r["summary"].get("workers", 1) > 1 for r in all_results.values())
    execution_mode = "Parallel" if parallel_used else "Sequential"
    
    # Determine which time to show as primary
    if wall_clock_time is not None and execution_mode == "Parallel":
        primary_time = wall_clock_time
        primary_time_label = "Wall-Clock Time (Actual)"
        secondary_time = total_time
        secondary_time_label = "Sum of Test Times"
        speedup = total_time / wall_clock_time if wall_clock_time > 0 else 1.0
    else:
        primary_time = total_time
        primary_time_label = "Total Execution Time"
        secondary_time = None
        secondary_time_label = None
        speedup = None
    
    report = f"""# Test Execution Master Summary

**Generated:** {timestamp}  
**Execution Mode:** {execution_mode}
**{primary_time_label}:** {primary_time:.2f} seconds ({primary_time/60:.1f} minutes)
"""
    
    if secondary_time is not None:
        report += f"**{secondary_time_label}:** {secondary_time:.2f} seconds ({secondary_time/60:.1f} minutes)  \n"
        report += f"**Parallel Speedup:** {speedup:.2f}x  \n"
    
    report += f"""**Total Tests:** {total_tests}  
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
        # Use summary counts (passed + failed) as authoritative, fallback to results length
        passed_count = summary.get('passed', 0)
        failed_count = summary.get('failed', 0)
        num_tests = passed_count + failed_count
        if num_tests == 0:
            num_tests = len(results)  # Fallback to results count if summary doesn't have counts
        exec_time = summary.get("total_time", 0)
        # If exec_time is 0 but we have results, calculate from results
        if exec_time == 0.0 and results:
            exec_time = sum(r.duration for r in results)
        avg_time = exec_time / num_tests if num_tests > 0 else 0
        
        report += f"| **{category_name.upper()}** | {num_tests} | {passed_count} | {failed_count} | {exec_time:.2f}s | {avg_time:.2f}s |\n"
    
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

- **{primary_time_label}:** {primary_time:.2f} seconds ({primary_time/60:.1f} minutes)
"""
    
    if secondary_time is not None:
        report += f"- **{secondary_time_label}:** {secondary_time:.2f} seconds ({secondary_time/60:.1f} minutes)\n"
        if speedup >= 1.0:
            report += f"- **Parallel Speedup:** {speedup:.2f}x (tests ran {speedup:.1f}x faster due to parallelism)\n"
        elif speedup > 0:
            report += f"- **Parallel Overhead:** {1/speedup:.2f}x (parallel overhead for small test suite - sequential would be faster)\n"
        else:
            report += f"- **Note:** Unable to calculate speedup (test execution time was 0)\n"
    
    report += f"""- **Average Time per Test:** {(total_time/total_tests if total_tests > 0 else 0):.2f}s ({total_tests} tests)
- **Success Rate:** {(total_passed/total_tests*100 if total_tests > 0 else 0):.1f}% ({total_passed}/{total_tests})
- **Categories Tested:** {len(all_results)}
- **Execution Mode:** {execution_mode}
"""
    
    if parallel_used:
        max_workers = max(r["summary"].get("workers", 1) for r in all_results.values())
        report += f"- **Max Parallel Workers:** {max_workers}\n"
    
    report += """
## Recommendations

"""
    
    if total_failed > 0:
        report += f"- [WARN] {total_failed} test(s) failed - review and fix\n"
    
    if all_slowest:
        slowest = all_slowest[0]
        if slowest[1].duration > 10.0:
            report += f"- [SLOW] Slowest test: `{slowest[1].name}` ({slowest[1].duration:.2f}s) - consider optimization\n"
    
    if total_time > 300:  # 5 minutes
        report += f"- [TIME] Total execution time is {total_time/60:.1f} minutes - parallel execution already enabled\n"
    
    report += """
## Category Reports

For detailed reports, see:
"""
    
    for category_name, data in sorted(all_results.items()):
        report_path = data["report_path"]
        # Convert to relative path from docs/test-reports/ to tests/{category}/
        relative_path = f"../../{report_path}"
        report += f"- **[{category_name.upper()}]({relative_path})**\n"
    
    # Write master summary
    master_path = project_root / "docs/test-reports/TEST_EXECUTION_MASTER_SUMMARY.md"
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_text(report, encoding='utf-8')
    print(f"\n[OK] Master summary generated: {master_path}")
    if wall_clock_time is not None and execution_mode == "Parallel":
        print(f"     Wall-Clock Time (Actual): {wall_clock_time:.2f} seconds ({wall_clock_time/60:.1f} minutes)")
        print(f"     Sum of Test Times: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        if speedup and speedup > 0:
            if speedup >= 1.0:
                print(f"     Parallel Speedup: {speedup:.2f}x")
            else:
                print(f"     Parallel Overhead: {1/speedup:.2f}x (sequential would be faster)")
        else:
            print(f"     Note: Unable to calculate speedup (test execution time was 0)")
    else:
        print(f"     Total Execution Time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
    print(f"     Total Tests: {total_tests} (Passed: {total_passed}, Failed: {total_failed})")
    if parallel_used:
        print(f"     Execution Mode: Parallel")


def main():
    """Main test runner with parallel execution support."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run tests with parallel execution')
    parser.add_argument('--category', type=str, help='Run specific category only')
    parser.add_argument('--workers', type=int, help='Number of parallel workers per category (default: auto)')
    parser.add_argument('--no-category-parallel', action='store_true', 
                       help='Disable parallel execution of categories (run sequentially)')
    parser.add_argument('--no-test-parallel', action='store_true',
                       help='Disable parallel execution within categories (use sequential)')
    
    args = parser.parse_args()
    
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
    
    # Filter categories if specific one requested
    if args.category:
        category_name = args.category.lower()
        if category_name in categories:
            categories = {category_name: categories[category_name]}
        else:
            print(f"Unknown category: {category_name}")
            print(f"Available categories: {', '.join(categories.keys())}")
            return 1
    
    # Check pytest-xdist availability
    has_xdist = check_pytest_xdist()
    use_test_parallel = not args.no_test_parallel and has_xdist
    
    if not has_xdist and not args.no_test_parallel:
        print("\n[INFO] pytest-xdist not installed. Install with: pip install pytest-xdist")
        print("[INFO] Tests will run sequentially within each category.\n")
    
    # Run tests
    all_results = {}
    start_time = time.time()
    
    if args.no_category_parallel or len(categories) == 1:
        # Sequential category execution
        print("\n" + "="*70)
        print("Running test categories sequentially...")
        print("="*70)
        for category_name, config in categories.items():
            result = run_category_tests(category_name, config, args.workers, use_test_parallel)
            all_results[category_name] = result
    else:
        # Parallel category execution
        print("\n" + "="*70)
        print(f"Running {len(categories)} test categories in parallel...")
        print("="*70)
        
        # Determine max workers for category-level parallelism
        import os
        max_category_workers = min(len(categories), os.cpu_count() or 2)
        
        with ThreadPoolExecutor(max_workers=max_category_workers) as executor:
            # Submit all category tests
            future_to_category = {
                executor.submit(run_category_tests, cat_name, config, args.workers, use_test_parallel): cat_name
                for cat_name, config in categories.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_category):
                category_name = future_to_category[future]
                try:
                    result = future.result()
                    all_results[category_name] = result
                    print(f"\n[✓] {category_name.upper()} tests completed")
                except Exception as e:
                    print(f"\n[✗] {category_name.upper()} tests failed: {e}")
                    all_results[category_name] = {
                        "results": [],
                        "summary": {"total_time": 0.0, "passed": 0, "failed": 0, "error": str(e)},
                        "report_path": categories[category_name]["report_path"]
                    }
    
    total_elapsed = time.time() - start_time
    
    # Generate master summary (pass wall-clock time for parallel execution)
    generate_master_summary(all_results, wall_clock_time=total_elapsed)
    
    print(f"\n{'='*70}")
    print(f"Total wall-clock time: {total_elapsed:.2f} seconds ({total_elapsed/60:.1f} minutes)")
    print(f"{'='*70}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

