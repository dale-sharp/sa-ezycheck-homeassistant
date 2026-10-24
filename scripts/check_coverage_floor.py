"""
Fail CI if any module falls below the per-module coverage floor in CONTRIBUTING.md.

pytest-cov/coverage.py only supports a single overall `fail_under` threshold; it has no
built-in way to gate an individual file's coverage percentage. CONTRIBUTING.md documents
two separate thresholds ("95% overall, no module below ~90%"); the overall one is
enforced by `fail_under` in pyproject.toml, and this script enforces the per-module one
against the `coverage.json` report produced by the same run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PER_MODULE_FLOOR = 90.0
COVERAGE_JSON_PATH = Path("coverage.json")


def main() -> int:
    """Return a non-zero exit code if any module is below the floor."""
    report = json.loads(COVERAGE_JSON_PATH.read_text(encoding="utf-8"))

    failures = [
        (path, file_report["summary"]["percent_covered"])
        for path, file_report in report["files"].items()
        if file_report["summary"]["percent_covered"] < PER_MODULE_FLOOR
    ]

    if failures:
        sys.stdout.write(
            f"Modules below the {PER_MODULE_FLOOR}% per-module coverage floor:\n"
        )
        for path, percent in failures:
            sys.stdout.write(f"  {path}: {percent:.1f}%\n")
        return 1

    sys.stdout.write(
        f"All modules meet the {PER_MODULE_FLOOR}% per-module coverage floor.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
