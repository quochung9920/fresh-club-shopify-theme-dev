#!/usr/bin/env python3
"""Prevent feature PRs from silently rewriting the Theme Check baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from theme_check_regression import load_baseline, load_report

ROOT = Path(__file__).resolve().parents[1]
SHOPIFY_CLI = ROOT / "node_modules" / "@shopify" / "cli" / "bin" / "run.js"
SHOPIFY_PACKAGE = ROOT / "node_modules" / "@shopify" / "cli" / "package.json"
LOCKED_SHOPIFY_VERSION = "4.7.0"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def verify_bootstrap_offenses(baseline: Path, source_commit: str) -> None:
    if not SHOPIFY_CLI.is_file() or not SHOPIFY_PACKAGE.is_file():
        raise ValueError("locked Shopify CLI is missing; run npm ci --ignore-scripts")
    package = json.loads(SHOPIFY_PACKAGE.read_text(encoding="utf-8"))
    if package.get("version") != LOCKED_SHOPIFY_VERSION:
        raise ValueError(
            f"installed Shopify CLI must be exactly {LOCKED_SHOPIFY_VERSION}, "
            f"found {package.get('version')!r}"
        )

    with tempfile.TemporaryDirectory(prefix="fresh-club-baseline-") as temp_dir:
        temp_root = Path(temp_dir)
        worktree = temp_root / "source-theme"
        report = temp_root / "source-theme-check.json"
        git("worktree", "add", "--detach", str(worktree), source_commit)
        try:
            completed = subprocess.run(
                [
                    "node", str(SHOPIFY_CLI), "theme", "check",
                    "--output", "json", "--no-color", "--path", str(worktree),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            report.write_text(completed.stdout, encoding="utf-8", newline="\n")
            if completed.returncode not in {0, 1}:
                raise ValueError(
                    "Theme Check failed while reproducing bootstrap baseline: "
                    f"exit={completed.returncode}; stderr={completed.stderr.strip()}"
                )
            actual = load_report(report, root=worktree)
            expected = load_baseline(baseline)
            if actual != expected:
                added = actual - expected
                inflated = expected - actual
                raise ValueError(
                    "bootstrap baseline offenses do not exactly match Theme Check at "
                    f"source_commit (missing_or_increased={sum(inflated.values())}, "
                    f"unexpected_current={sum(added.values())})"
                )
        finally:
            git("worktree", "remove", "--force", str(worktree), check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=ROOT / ".theme-check-baseline.json")
    parser.add_argument("--base-ref")
    args = parser.parse_args()

    baseline = args.baseline.resolve()
    data = json.loads(baseline.read_text(encoding="utf-8"))
    source_commit = data.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("baseline source_commit must be a lowercase full 40-character commit SHA")
    git("cat-file", "-e", f"{source_commit}^{{commit}}")

    if not args.base_ref:
        print(f"Baseline metadata valid; source commit exists: {source_commit}")
        return 0

    git("rev-parse", "--verify", f"{args.base_ref}^{{commit}}")
    relative = baseline.relative_to(ROOT).as_posix()
    existing = git("show", f"{args.base_ref}:{relative}", check=False)
    current_bytes = baseline.read_bytes()

    if existing.returncode == 0:
        if existing.stdout.encode("utf-8") != current_bytes:
            raise ValueError(
                "Theme Check baseline differs from the PR base. Baseline changes are blocked in normal PRs."
            )
        print("Theme Check baseline is byte-identical to the PR base")
        return 0

    base_commit = git("rev-parse", args.base_ref).stdout.strip()
    ancestry = git("merge-base", "--is-ancestor", source_commit, "HEAD", check=False)
    if ancestry.returncode != 0:
        raise ValueError(
            "Bootstrap baseline source_commit must be an ancestor of the proposed PR commit"
        )
    verify_bootstrap_offenses(baseline, source_commit)
    print(
        "Theme Check bootstrap baseline exactly reproduced from source commit "
        f"{source_commit} for base {base_commit}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"Theme Check baseline verification failed: {exc}")
        raise SystemExit(1)
