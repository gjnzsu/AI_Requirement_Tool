"""Offline checks for the actual embedded CD URL validator and Bash syntax."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / '.github/workflows/cd.yml').read_text()
VALIDATOR = WORKFLOW.split("          python3 - <<'PY'\n", 1)[1].split(
    '          PY\n', 1
)[0]
VALIDATOR = '\n'.join(line[10:] for line in VALIDATOR.splitlines())


class GatewayWorkflowTests(unittest.TestCase):
    def test_actual_validator(self):
        for value, valid in (
            ('https://requirement.example.com/', True),
            ('http://localhost:8080', True),
            ('', False),
            ('host-only', False),
            ('ftp://example.com', False),
            ('https://user:pass@example.com', False),
            ('https://example.com/api', False),
            ('https://example.com?x=1', False),
            ('https://example.com#fragment', False),
            ('https://example.com?', False),
            ('https://example.com:invalid', False),
            ('https://example.com\nINJECTED=1', False),
        ):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'github-env'
                result = subprocess.run(
                    [sys.executable, '-c', VALIDATOR],
                    env=dict(os.environ, REQUESTED_BASE_URL=value, GITHUB_ENV=str(output)),
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode == 0, valid, result.stderr)
                if valid:
                    self.assertEqual(output.read_text(), f"BASE_URL={value.rstrip('/')}\n")
                else:
                    self.assertFalse(output.exists())

    def test_bash_syntax(self):
        bash = Path('C:/Program Files/Git/bin/bash.exe')
        if not bash.exists():
            self.skipTest('Git Bash unavailable')
        blocks = []
        current = None
        for line in WORKFLOW.splitlines():
            if line == '        run: |':
                current = []
                blocks.append(current)
            elif current is not None:
                if line.startswith('          '):
                    current.append(line[10:])
                elif line.strip():
                    current = None
        for index, block in enumerate(blocks):
            with self.subTest(block=index):
                result = subprocess.run(
                    [str(bash), '-n'], input='\n'.join(block) + '\n',
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
