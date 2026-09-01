#!/usr/bin/env python3
"""Fail-closed structural and high-confidence secret checks for the theme."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRS = ("assets", "config", "layout", "locales", "sections", "snippets", "templates")
JSON_DIRS = ("config", "locales", "sections", "templates")
EXCLUDED_ROOT_DIRS = {".git", "node_modules", "__pycache__", ".shopify"}
SECRET_NAME_PATTERNS = (
    re.compile(r"^\.env(?:\..+)?$", re.IGNORECASE),
    re.compile(r"^(?:id_rsa|id_ed25519)(?:\.pub)?$", re.IGNORECASE),
    re.compile(r".*(?:credential|private[_-]?key|service[_-]?account|secrets?).*", re.IGNORECASE),
    re.compile(r".*\.(?:pem|p12|pfx|key)$", re.IGNORECASE),
)
SECRET_CONTENT_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "Shopify access token": re.compile(rb"\b(?:shpat|shpca|shppa|shpss)_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}

errors: list[str] = []

for dirname in REQUIRED_DIRS:
    if not (ROOT / dirname).is_dir():
        errors.append(f"missing required theme directory: {dirname}/")

for dirname in JSON_DIRS:
    base = ROOT / dirname
    if not base.exists():
        continue
    for path in sorted(base.rglob("*.json")):
        try:
            text = path.read_text(encoding="utf-8-sig")
            # Shopify-generated JSON can start with one informational block
            # comment. Strip only that header, then require strict JSON.
            text = re.sub(r"^\s*/\*.*?\*/\s*", "", text, count=1, flags=re.DOTALL)
            json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid Shopify JSON: {path.relative_to(ROOT).as_posix()}: {exc}")

scanned_files = 0
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    relative_parts = path.relative_to(ROOT).parts
    if relative_parts and relative_parts[0] in EXCLUDED_ROOT_DIRS:
        continue
    relpath = path.relative_to(ROOT).as_posix()
    if any(pattern.fullmatch(path.name) for pattern in SECRET_NAME_PATTERNS):
        errors.append(f"forbidden credential-like filename: {relpath}")
        continue
    try:
        data = path.read_bytes()
    except OSError as exc:
        errors.append(f"could not read file during secret scan: {relpath}: {exc}")
        continue
    scanned_files += 1
    for label, pattern in SECRET_CONTENT_PATTERNS.items():
        if pattern.search(data):
            errors.append(f"high-confidence {label} detected in: {relpath}")

if errors:
    print("Theme structure validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

json_count = sum(1 for dirname in JSON_DIRS for _ in (ROOT / dirname).rglob("*.json"))
print("Theme structure validation passed")
print(f"Required directories: {len(REQUIRED_DIRS)}")
print(f"JSON files parsed: {json_count}")
print(f"Files scanned for high-confidence secrets: {scanned_files}")
