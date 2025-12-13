#!/usr/bin/env python3
"""
Aggregate per-category TEST_EXECUTION_SUMMARY.md files and update
tests/TEST_EXECUTION_MASTER_SUMMARY.md with accurate execution times.

Usage: python scripts/update_test_summary.py
"""
from pathlib import Path
import re
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
MASTER = ROOT / "docs" / "test-reports" / "TEST_EXECUTION_MASTER_SUMMARY.md"


def parse_time_str(s: str) -> float:
    """Parse a time like '49.37s' or '0.00 seconds' to seconds as float."""
    if s is None:
        return 0.0
    s = s.strip()
    m = re.search(r"([0-9]+\.?[0-9]*)\s*(s|seconds)?", s)
    if not m:
        return 0.0
    return float(m.group(1))


def find_category_summaries():
    # Find all TEST_EXECUTION_SUMMARY.md except the master
    return [p for p in TESTS_DIR.rglob("TEST_EXECUTION_SUMMARY.md") if p != MASTER]


def parse_category_file(path: Path):
    text = path.read_text(encoding="utf-8")
    # category name from parent dir (last part), uppercase
    category = path.parent.name.upper()

    # Try to extract 'Total Tests' and 'Total Execution Time'
    tests = 0
    exec_time = 0.0
    passed = None
    failed = None

    m_tests = re.search(r"\*\*Total Tests:\*\*\s*(\d+)", text)
    if m_tests:
        tests = int(m_tests.group(1))

    m_passed = re.search(r"\*\*Passed:\*\*\s*(\d+)", text)
    if m_passed:
        passed = int(m_passed.group(1))
    m_failed = re.search(r"\*\*Failed:\*\*\s*(\d+)", text)
    if m_failed:
        failed = int(m_failed.group(1))

    # Try multiple patterns to extract execution time
    # Pattern 1: "**Total Execution Time:** 12.34 seconds" or "**Total Execution Time:** 12.34s"
    m_time = re.search(r"\*\*Total Execution Time:\*\*\s*([0-9\.]+)\s*(?:seconds|s)?", text)
    if m_time:
        exec_time = float(m_time.group(1))
    else:
        # Pattern 2: Look in "Performance Statistics" section: "- **Total Time:** 12.34 seconds"
        m_time2 = re.search(r"- \*\*Total Time:\*\*\s*([0-9\.]+)\s*(?:seconds|s)?", text)
        if m_time2:
            exec_time = float(m_time2.group(1))
        else:
            # Pattern 3: Look for a table row containing 'Execution Time' value
            # pattern: | **CAT** | tests | passed | failed | 12.34s | 6.17s |
            m_row = re.search(r"^\|\s*\*\*(?P<cat>[^*]+)\*\*.*\|\s*([0-9\.]+s)\s*\|", text, re.M)
            if m_row:
                exec_time = parse_time_str(m_row.group(2))
            else:
                exec_time = 0.0

    return dict(category=category, tests=tests, passed=passed, failed=failed, exec_time=exec_time, path=path)


def format_seconds(s: float) -> str:
    return f"{s:.2f}s"


def main():
    if not MASTER.exists():
        print(f"Master summary {MASTER} not found")
        return 1

    # Backup (write a .bak copy, don't replace the master file)
    bak = MASTER.with_suffix(MASTER.suffix + ".bak")
    bak.write_text(MASTER.read_text(encoding="utf-8"), encoding="utf-8")

    cat_files = find_category_summaries()
    cats = [parse_category_file(p) for p in cat_files]

    total_time = sum(c.get("exec_time", 0.0) for c in cats)
    total_tests = 0
    # if master contains a Total Tests line, keep that as authoritative fallback
    master_text = MASTER.read_text(encoding="utf-8")
    m_master_tests = re.search(r"\*\*Total Tests:\*\*\s*(\d+)", master_text)
    if m_master_tests:
        total_tests = int(m_master_tests.group(1))
    else:
        total_tests = sum(c.get("tests", 0) for c in cats)

    avg_per_test = (total_time / total_tests) if total_tests else 0.0

    # Update master content
    new_text = master_text

    # Update generated timestamp
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_text = re.sub(r"\*\*Generated:.*", f"**Generated:** {now}", new_text)

    # Update header total execution time (first occurrence)
    new_text = re.sub(r"\*\*Total Execution Time:\*\*.*", f"**Total Execution Time:** {total_time:.2f} seconds ", new_text, count=1)

    # Update summary by category table rows
    for c in cats:
        cat = c["category"]
        tests = c.get("tests", 0)
        et = c.get("exec_time", 0.0)
        avg = (et / tests) if tests else 0.0
        # replace row like: | **AGENT** | 2 | 2 | 0 | 0.00s | 0.00s |
        pattern = re.compile(rf"^\|\s*\*\*{re.escape(cat)}\*\*\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*[^|]+\|\s*[^|]+\|", re.M)
        repl = f"| **{cat}** | {tests} | {c.get('passed') or 0} | {c.get('failed') or 0} | {format_seconds(et)} | {format_seconds(avg)} |"
        new_text, n = pattern.subn(repl, new_text)
        if n == 0:
            # try to replace by looking for a row starting with the category name without bold
            pattern2 = re.compile(rf"^\|\s*{re.escape(cat)}\s*\|.*", re.M)
            new_text = pattern2.sub(repl, new_text)

    # Update slowest tests percentages
    def repl_slow(m):
        time_s = parse_time_str(m.group('time'))
        pct = (time_s / total_time * 100) if total_time else 0.0
        return f"**{time_s:.2f}s** | {pct:.1f}% |"

    new_text = re.sub(r"\*\*(?P<time>[0-9\.]+)s\*\*\s*\|\s*[0-9\.]+%\s*\|", repl_slow, new_text)

    # Update overall statistics block
    new_text = re.sub(r"- \*\*Total Execution Time:\*\*.*", f"- **Total Execution Time:** {total_time:.2f} seconds ({total_time/60:.1f} minutes)", new_text)
    new_text = re.sub(r"- \*\*Average Time per Test:\*\*.*", f"- **Average Time per Test:** {avg_per_test:.2f}s ({total_tests} tests)", new_text)

    # Write back
    MASTER.write_text(new_text, encoding="utf-8")
    print(f"Updated {MASTER} (backup at {bak})")


if __name__ == '__main__':
    raise SystemExit(main())
