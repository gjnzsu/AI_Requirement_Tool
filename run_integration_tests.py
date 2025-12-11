"""Run only integration tests."""

import sys
from run_tests import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--integration"]
    sys.exit(main())

