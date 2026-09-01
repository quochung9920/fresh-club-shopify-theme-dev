#!/usr/bin/env python3
"""Reject Theme Check offenses not present in the reviewed baseline."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
THEME_DIRS = {"assets", "config", "layout", "locales", "sections", "snippets", "templates"}
SEVERITIES = {"error", "warning", "info", "style", "suggestion", "crash"}
REPORT_FILE_KEYS = {"path", "offenses", "errorCount", "warningCount", "infoCount"}
REPORT_OFFENSE_KEYS = {
    "check", "severity", "message",
    "start_row", "start_column", "end_row", "end_column",
}
BASELINE_KEYS = {"version", "source_commit", "policy", "offenses"}
BASELINE_OFFENSE_KEYS = {"path", "check", "severity", "message", "count"}
Signature = tuple[str, str, str, str]


def require_nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def relative_theme_path(raw: str, root: Path = ROOT) -> str:
    normalized = raw.replace("\\", "/")
    native_path = Path(raw)
    is_windows_absolute = re.match(r"^[A-Za-z]:/", normalized) is not None

    if native_path.is_absolute() or is_windows_absolute:
        try:
            relative = native_path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError) as exc:
            raise ValueError(
                f"Theme Check absolute path is outside the validated theme root: {raw!r}"
            ) from exc
    else:
        relative = normalized

    pure = PurePosixPath(relative)
    if (
        not relative
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.parts[0] not in THEME_DIRS
    ):
        raise ValueError(f"Theme Check path is outside standard theme directories: {raw!r}")
    return pure.as_posix()


def read_json(path: Path, label: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON at {path}: {exc}") from exc


def load_report(path: Path, root: Path = ROOT) -> Counter[Signature]:
    data = read_json(path, "Theme Check report")
    if not isinstance(data, list):
        raise ValueError("Theme Check report root must be a JSON list")
    offenses: Counter[Signature] = Counter()
    for file_index, file_report in enumerate(data):
        if not isinstance(file_report, dict):
            raise ValueError(f"report[{file_index}] must be an object")
        if "path" not in file_report or "offenses" not in file_report:
            raise ValueError(f"report[{file_index}] must contain path and offenses")
        unknown = file_report.keys() - REPORT_FILE_KEYS
        if unknown:
            raise ValueError(f"report[{file_index}] has unknown fields: {sorted(unknown)}")
        for count_field in ("errorCount", "warningCount", "infoCount"):
            if count_field in file_report:
                count = file_report[count_field]
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError(
                        f"report[{file_index}].{count_field} must be a non-negative integer"
                    )
        raw_path = require_nonempty_string(file_report["path"], f"report[{file_index}].path")
        relpath = relative_theme_path(raw_path, root=root)
        file_offenses = file_report["offenses"]
        if not isinstance(file_offenses, list):
            raise ValueError(f"report[{file_index}].offenses must be a list")
        for offense_index, offense in enumerate(file_offenses):
            prefix = f"report[{file_index}].offenses[{offense_index}]"
            if not isinstance(offense, dict):
                raise ValueError(f"{prefix} must be an object")
            missing = {"check", "severity", "message"} - offense.keys()
            if missing:
                raise ValueError(f"{prefix} missing fields: {sorted(missing)}")
            unknown = offense.keys() - REPORT_OFFENSE_KEYS
            if unknown:
                raise ValueError(f"{prefix} has unknown fields: {sorted(unknown)}")
            for position_field in ("start_row", "start_column", "end_row", "end_column"):
                if position_field in offense:
                    position = offense[position_field]
                    if isinstance(position, bool) or not isinstance(position, int) or position < 0:
                        raise ValueError(f"{prefix}.{position_field} must be a non-negative integer")
            check = require_nonempty_string(offense["check"], f"{prefix}.check")
            severity = require_nonempty_string(offense["severity"], f"{prefix}.severity")
            message = require_nonempty_string(offense["message"], f"{prefix}.message")
            if severity not in SEVERITIES:
                raise ValueError(f"{prefix}.severity is unsupported: {severity!r}")
            offenses[(relpath, check, severity, message)] += 1
    return offenses


def load_baseline(path: Path) -> Counter[Signature]:
    data = read_json(path, "baseline")
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("baseline must be an object with version=1")
    unknown = data.keys() - BASELINE_KEYS
    if unknown:
        raise ValueError(f"baseline has unknown fields: {sorted(unknown)}")
    require_nonempty_string(data.get("policy"), "baseline.policy")
    if not isinstance(data.get("source_commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", data["source_commit"]):
        raise ValueError("baseline source_commit must be a lowercase full 40-character commit SHA")
    items = data.get("offenses")
    if not isinstance(items, list):
        raise ValueError("baseline offenses must be a list")
    result: Counter[Signature] = Counter()
    for index, item in enumerate(items):
        prefix = f"baseline.offenses[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{prefix} must be an object")
        missing = {"path", "check", "severity", "message", "count"} - item.keys()
        if missing:
            raise ValueError(f"{prefix} missing fields: {sorted(missing)}")
        unknown = item.keys() - BASELINE_OFFENSE_KEYS
        if unknown:
            raise ValueError(f"{prefix} has unknown fields: {sorted(unknown)}")
        signature = (
            relative_theme_path(require_nonempty_string(item["path"], f"{prefix}.path")),
            require_nonempty_string(item["check"], f"{prefix}.check"),
            require_nonempty_string(item["severity"], f"{prefix}.severity"),
            require_nonempty_string(item["message"], f"{prefix}.message"),
        )
        if signature[2] not in SEVERITIES:
            raise ValueError(f"{prefix}.severity is unsupported: {signature[2]!r}")
        count = item["count"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError(f"{prefix}.count must be a positive integer")
        if signature in result:
            raise ValueError(f"duplicate baseline signature at {prefix}")
        result[signature] = count
    return result


def write_baseline(path: Path, offenses: Counter[Signature], source_commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("--source-commit must be a lowercase full 40-character commit SHA")
    items = [
        {"path": key[0], "check": key[1], "severity": key[2], "message": key[3], "count": count}
        for key, count in sorted(offenses.items())
    ]
    payload = {
        "version": 1,
        "source_commit": source_commit,
        "policy": "No offense signature count may exceed this reviewed imported-theme baseline.",
        "offenses": items,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--source-commit", default="unknown")
    args = parser.parse_args()

    current = load_report(args.report)
    if args.update_baseline:
        write_baseline(args.baseline, current, args.source_commit)
        print(f"Wrote reviewed baseline with {sum(current.values())} offenses")
        return 0

    baseline = load_baseline(args.baseline)
    new = current - baseline
    resolved = baseline - current
    print(f"Theme Check offenses: current={sum(current.values())}, baseline={sum(baseline.values())}")
    print(f"Resolved baseline offenses: {sum(resolved.values())}")
    if not new:
        print("Theme Check regression passed: no new offense signatures")
        return 0

    print(f"Theme Check regression failed: {sum(new.values())} new offense(s)")
    for (path, check, severity, message), count in sorted(new.items()):
        print(f"- {path}: {severity} {check} x{count}: {message}")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"Theme Check regression input validation failed: {exc}")
        raise SystemExit(2)
