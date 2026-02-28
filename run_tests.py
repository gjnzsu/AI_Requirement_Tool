"""
Test runner script to execute all tests or specific test categories.

Usage:
    python run_tests.py                    # Run all tests (fast tests only, parallel execution)
    python run_tests.py --slow             # Run slow tests (includes E2E tests with real API calls)
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --e2e              # Run only e2e tests
    python run_tests.py --mcp              # Run MCP tests
    python run_tests.py --rag              # Run RAG tests
    python run_tests.py --agent            # Run agent tests
    python run_tests.py --llm              # Run LLM tests
    python run_tests.py --memory           # Run memory tests

Parallel Execution:
    Tests run in parallel by default using pytest-xdist (if available).
    Use -n auto to automatically detect CPU cores, or -n N to use N workers.
    Falls back to sequential execution if pytest-xdist is not installed.

Slow Tests:
    Slow tests (marked with @pytest.mark.slow) are skipped by default.
    These include tests with real LLM API calls (RAG, Coze E2E).
    Use --slow flag to include slow tests in the run.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_pytest_xdist():
    """Check if pytest-xdist is available."""
    try:
        import xdist
        return True
    except ImportError:
        return False


def run_pytest(args, use_parallel=True):
    """Run pytest with given arguments.
    
    Args:
        args: List of pytest arguments
        use_parallel: If True, enable parallel execution with pytest-xdist if available
    """
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add parallel execution if pytest-xdist is available and not already specified
    if use_parallel and check_pytest_xdist():
        # Check if -n flag is already in args
        has_n_flag = any(arg.startswith('-n') for arg in args)
        if not has_n_flag:
            cmd.extend(["-n", "auto"])
            print("Note: Running tests in parallel (pytest-xdist)")
    
    # Add the rest of the arguments
    cmd.extend(args)
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 70)
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def run_unittest(args):
    """Run unittest with given arguments."""
    cmd = [sys.executable, "-m", "unittest"] + args
    print(f"Running: {' '.join(cmd)}")
    print("=" * 70)
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def main():
    """Main test runner."""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "--slow":
            # Run all tests including slow ones
            return run_pytest(["tests/", "-v", "-m", "slow"])
        elif arg == "--unit":
            return run_pytest(["tests/unit/", "-v"])
        elif arg == "--integration":
            return run_pytest(["tests/integration/", "-v"])
        elif arg == "--e2e":
            return run_pytest(["tests/e2e/", "-v"])
        elif arg == "--mcp":
            return run_pytest(["tests/integration/mcp/", "-v"])
        elif arg == "--rag":
            return run_pytest(["tests/integration/rag/", "-v", "-m", "rag"])
        elif arg == "--agent":
            return run_pytest(["tests/integration/agent/", "-v", "-m", "agent"])
        elif arg == "--llm":
            return run_pytest(["tests/integration/llm/", "-v", "-m", "llm"])
        elif arg == "--memory":
            return run_pytest(["tests/integration/memory/", "-v", "-m", "memory"])
        elif arg == "--help" or arg == "-h":
            print(__doc__)
            return 0
        else:
            print(f"Unknown option: {arg}")
            print(__doc__)
            return 1
    else:
        # Run all tests (fast tests only, slow tests skipped by default via pytest.ini)
        # Disable parallel (use_parallel=False) so async tests run in main process and
        # avoid "Runner.run() cannot be called from a running event loop" with pytest-xdist
        return run_pytest(["tests/", "-v"], use_parallel=False)


if __name__ == "__main__":
    sys.exit(main())

