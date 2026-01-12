"""
Test runner script to execute all tests or specific test categories.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --e2e              # Run only e2e tests
    python run_tests.py --mcp              # Run MCP tests
    python run_tests.py --rag              # Run RAG tests
    python run_tests.py --agent            # Run agent tests
    python run_tests.py --llm              # Run LLM tests
    python run_tests.py --memory           # Run memory tests
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_pytest(args):
    """Run pytest with given arguments."""
    cmd = [sys.executable, "-m", "pytest"] + args
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
        
        if arg == "--unit":
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
        # Run all tests
        return run_pytest(["tests/", "-v"])


if __name__ == "__main__":
    sys.exit(main())

