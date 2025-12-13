# Parallel Test Execution Guide

## Overview

The test suite supports parallel execution at two levels to significantly reduce test execution time:

1. **Category-level parallelism**: Run multiple test categories simultaneously (unit, llm, memory, rag, agent, api, mcp)
2. **Test-level parallelism**: Run tests within each category in parallel using pytest-xdist

## Installation

Install the required dependency for parallel test execution:

```bash
pip install pytest-xdist
```

Or install all test dependencies:

```bash
pip install -r requirements-test.txt
```

## Usage

### PowerShell Script (Recommended)

**Sequential execution (default):**
```powershell
.\run_tests.ps1
```

**Parallel execution:**
```powershell
# Run all categories in parallel with auto-detected workers
.\run_tests.ps1 -Parallel

# Run specific category in parallel
.\run_tests.ps1 -Category unit -Parallel

# Run with specific number of workers per category
.\run_tests.ps1 -Parallel -Workers 4
```

### Python Scripts

**Parallel execution:**
```bash
# Run all categories in parallel
python scripts/run_tests_with_timing_parallel.py

# Run specific category
python scripts/run_tests_with_timing_parallel.py --category unit

# Run with specific number of workers
python scripts/run_tests_with_timing_parallel.py --workers 4

# Disable category-level parallelism (run categories sequentially)
python scripts/run_tests_with_timing_parallel.py --no-category-parallel

# Disable test-level parallelism (run tests sequentially within categories)
python scripts/run_tests_with_timing_parallel.py --no-test-parallel
```

**Sequential execution (original):**
```bash
python scripts/run_tests_with_timing.py
```

## Performance Benefits

### Expected Speedup

- **Category-level parallelism**: ~2-3x speedup (depends on number of CPU cores)
- **Test-level parallelism**: ~2-4x speedup per category (depends on number of tests and CPU cores)
- **Combined**: Up to **5-10x speedup** for full test suite

### Example Execution Times

| Mode | Estimated Time | Notes |
|------|---------------|-------|
| Sequential | ~4-5 minutes | All tests run one after another |
| Category Parallel | ~2-3 minutes | Categories run simultaneously |
| Full Parallel | ~1-2 minutes | Categories + tests run in parallel |

*Actual times depend on your CPU cores, test complexity, and network latency for API tests.*

## How It Works

### Category-Level Parallelism

- Uses Python's `ThreadPoolExecutor` to run multiple test categories simultaneously
- Each category runs in its own thread
- Maximum workers limited by CPU count and number of categories
- Independent categories (unit, api) can run safely in parallel
- Categories with shared resources may need sequential execution

### Test-Level Parallelism

- Uses `pytest-xdist` plugin for parallel test execution within each category
- Automatically detects CPU count and uses appropriate number of workers
- Uses "worksteal" distribution for better load balancing
- Each worker runs tests in isolation

## Configuration

### Auto-Detection

The parallel runner automatically:
- Detects CPU count for optimal worker allocation
- Falls back to sequential execution if pytest-xdist is not installed
- Limits workers to reasonable numbers (max 4 per category by default)

### Manual Configuration

You can override auto-detection:

```bash
# Use 4 workers per category
python scripts/run_tests_with_timing_parallel.py --workers 4

# Run categories sequentially but tests in parallel
python scripts/run_tests_with_timing_parallel.py --no-category-parallel

# Run categories in parallel but tests sequentially
python scripts/run_tests_with_timing_parallel.py --no-test-parallel
```

## Compatibility

### When to Use Sequential Execution

Use sequential execution (`run_tests_with_timing.py`) when:
- Tests have shared state or resources
- Debugging test failures (easier to trace)
- Running on systems with limited resources
- pytest-xdist is not installed

### When to Use Parallel Execution

Use parallel execution (`run_tests_with_timing_parallel.py`) when:
- Tests are independent
- You want faster feedback
- Running CI/CD pipelines
- You have multiple CPU cores available

## Troubleshooting

### pytest-xdist Not Installed

If you see:
```
[WARN] pytest-xdist not installed. Install with: pip install pytest-xdist
[INFO] Running tests sequentially...
```

Install it:
```bash
pip install pytest-xdist
```

### Test Failures in Parallel Mode

Some tests may fail in parallel but pass sequentially due to:
- Shared state between tests
- Race conditions
- Resource conflicts

**Solution**: Run the failing test category sequentially to debug:
```bash
python scripts/run_tests_with_timing.py --category <category_name>
```

### High Memory Usage

Parallel execution uses more memory. If you encounter memory issues:
- Reduce number of workers: `--workers 2`
- Run categories sequentially: `--no-category-parallel`
- Run tests sequentially: `--no-test-parallel`

## Best Practices

1. **Start with sequential execution** to establish baseline
2. **Use parallel execution** for regular test runs
3. **Debug failures sequentially** for easier troubleshooting
4. **Monitor execution times** to optimize worker counts
5. **Keep tests independent** to maximize parallelization benefits

## Reports

Both sequential and parallel execution generate the same report format:
- Category summaries: `tests/{category}/TEST_EXECUTION_SUMMARY.md`
- Master summary: `docs/test-reports/TEST_EXECUTION_MASTER_SUMMARY.md`

Reports include execution mode information (Parallel/Sequential) and worker counts.

