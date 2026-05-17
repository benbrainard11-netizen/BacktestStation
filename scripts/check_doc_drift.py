"""Check for documentation drift against the live codebase.

Currently checks:
  1. Test count claims in README.md / docs/PROJECT_STATE.md / CLAUDE.md
     vs actual `pytest --collect-only` count.

Designed to be a standalone script — can be run manually, in CI, or as a
pre-commit hook. Exits non-zero if any drift is detected.

Usage:
    python scripts/check_doc_drift.py
    python scripts/check_doc_drift.py --strict   # also fail on near-misses
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "PROJECT_STATE.md",
    ROOT / "CLAUDE.md",
]

# Match patterns like "470 backend tests", "507 tests green", "target: 470 passed"
# Looks for an integer 100-9999 followed by indicators of test-count context.
TEST_COUNT_PATTERNS = [
    re.compile(r"(\d{3,4})\s+(?:backend\s+)?tests?\b", re.IGNORECASE),
    re.compile(r"target:\s+(\d{3,4})\s+passed", re.IGNORECASE),
    re.compile(r"\((\d{3,4})\s+currently\)", re.IGNORECASE),
    re.compile(r"\((\d{3,4})\s+tests?\s+green\)", re.IGNORECASE),
]


def collect_actual_test_count() -> int:
    """Run `pytest --collect-only` from backend/ and parse the count."""
    backend = ROOT / "backend"
    pytest = backend / ".venv" / "Scripts" / "pytest.exe"
    if not pytest.exists():
        pytest_cmd = ["pytest"]
    else:
        pytest_cmd = [str(pytest)]
    res = subprocess.run(
        [*pytest_cmd, "--collect-only", "-q"],
        cwd=str(backend),
        capture_output=True, text=True,
    )
    # Last line typically: "1015 tests collected in 2.04s"
    for line in res.stdout.splitlines()[::-1]:
        m = re.search(r"(\d+)\s+tests?\s+collected", line)
        if m:
            return int(m.group(1))
    raise RuntimeError(f"Could not parse pytest output:\n{res.stdout[-500:]}")


def find_claims_in_file(path: Path) -> list[tuple[int, int, str]]:
    """Return [(line_no, claimed_count, line_text)]."""
    if not path.exists():
        return []
    out: list[tuple[int, int, str]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for pat in TEST_COUNT_PATTERNS:
            for m in pat.finditer(line):
                # Filter false positives: ignore obviously irrelevant numbers
                # (years, asset counts, etc.). Heuristic: only flag if the line
                # contains "test" or "passed".
                if "test" not in line.lower() and "passed" not in line.lower():
                    continue
                out.append((i, int(m.group(1)), line.strip()))
                break  # one hit per line
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="Fail on any drift, even within +/-5 pct tolerance.")
    parser.add_argument("--tolerance", type=int, default=5,
                        help="Allowed drift in test count (default: 5).")
    args = parser.parse_args()

    print("Collecting actual test count...")
    try:
        actual = collect_actual_test_count()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"  pytest --collect-only: {actual} tests")

    drift_found = False
    print()
    for doc_path in DOC_FILES:
        claims = find_claims_in_file(doc_path)
        if not claims:
            continue
        rel = doc_path.relative_to(ROOT).as_posix()
        for line_no, claimed, text in claims:
            diff = abs(actual - claimed)
            if args.strict and diff > 0:
                drift = True
            else:
                drift = diff > args.tolerance
            tag = " DRIFT" if drift else " ok"
            print(f"{rel}:{line_no} claimed={claimed:>5} actual={actual:>5} diff={diff:+d}  [{tag}]")
            print(f"    {text[:120]}")
            if drift:
                drift_found = True

    print()
    if drift_found:
        print("FAIL: doc drift detected — update the docs (or use --tolerance to allow).")
        return 1
    print("OK: all doc test-count claims within tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
