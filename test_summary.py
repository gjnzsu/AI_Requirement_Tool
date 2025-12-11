"""
Test summary script - runs key tests and reports results.
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_test(test_path, description):
    """Run a test and return success status."""
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"File: {test_path}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(
            [sys.executable, str(test_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Check if test passed (exit code 0)
        if result.returncode == 0:
            print("✓ PASSED")
            return True
        else:
            print("✗ FAILED")
            # Print last few lines of output for context
            if result.stdout:
                lines = result.stdout.split('\n')
                print("\nLast output lines:")
                for line in lines[-10:]:
                    if line.strip():
                        print(f"  {line}")
            if result.stderr:
                lines = result.stderr.split('\n')
                print("\nErrors:")
                for line in lines[-5:]:
                    if line.strip():
                        print(f"  {line}")
            return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

def main():
    """Run key tests and summarize results."""
    print("="*70)
    print("TEST SUITE VERIFICATION")
    print("="*70)
    
    tests = [
        ("tests/unit/test_logger.py", "Logger Unit Test"),
        ("tests/integration/agent/test_agent_basic.py", "Agent Integration Test"),
        ("tests/integration/llm/test_openai_provider.py", "OpenAI Provider Test"),
    ]
    
    results = []
    for test_path, description in tests:
        test_file = project_root / test_path
        if test_file.exists():
            passed = run_test(test_file, description)
            results.append((description, passed))
        else:
            print(f"\n⚠ SKIPPED: {test_path} (file not found)")
            results.append((description, None))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for description, result in results:
        if result is True:
            status = "✓ PASSED"
        elif result is False:
            status = "✗ FAILED"
        else:
            status = "⚠ SKIPPED"
        print(f"  {status}: {description}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")
    print("="*70)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

