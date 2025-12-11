"""Run only unit tests."""

import sys
from run_tests import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--unit"]
    sys.exit(main())

