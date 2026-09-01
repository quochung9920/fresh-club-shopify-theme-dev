#!/usr/bin/env python3
"""Run locked Shopify Theme Check and enforce the reviewed regression baseline."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHOPIFY_CLI = ROOT / "node_modules" / "@shopify" / "cli" / "bin" / "run.js"
REGRESSION = ROOT / "scripts" / "theme_check_regression.py"
BASELINE = ROOT / ".theme-check-baseline.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=ROOT / "theme-check-report.json")
    args = parser.parse_args()

    if not SHOPIFY_CLI.is_file():
        print("Locked Shopify CLI is missing. Run: npm ci --ignore-scripts")
        return 2

    command = [
        "node", str(SHOPIFY_CLI), "theme", "check",
        "--output", "json", "--no-color", "--path", str(ROOT),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    args.report.write_text(completed.stdout, encoding="utf-8", newline="\n")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    print(f"Theme Check exit code: {completed.returncode}")
    print(f"Theme Check report: {args.report.resolve()}")
    if completed.returncode not in {0, 1}:
        print("Theme Check crashed or could not execute; refusing regression comparison")
        return completed.returncode or 2

    regression = subprocess.run(
        [
            sys.executable, str(REGRESSION),
            "--baseline", str(BASELINE),
            "--report", str(args.report),
        ],
        cwd=ROOT,
    )
    return regression.returncode


if __name__ == "__main__":
    raise SystemExit(main())
