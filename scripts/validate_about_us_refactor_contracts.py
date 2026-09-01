from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "about-us-native-refactor" / "contracts"
EXPECTED_TYPES = [
    "fc-about-hero",
    "fc-about-values",
    "fc-about-metrics",
    "fc-about-story",
    "fc-about-process",
    "fc-about-cta",
]
EXPECTED_NAMES = [
    "About — Hero",
    "About — Values",
    "About — Metrics",
    "About — Story",
    "About — Daily process",
    "About — Call to action",
]
EXPECTED_CONTRACT_HASHES = {
    "content-migration-contract.json": "a0a53f16f4cbf20ed976abb34c2c2653e04db5ba8d4d8da98b74b3812a4db33a",
    "editor-schema-contract.json": "4bac29dd982b965968ce9867528fe7623e3b00db742f35c277e60f65c28c873d",
    "file-ownership.json": "53b858f8d6eeeac773459a3859381f6e6e3d8cf5bcfb70d2f640d76ddc7cc27f",
    "interaction-contract.json": "bdef05f7d68b9cd8b69c86033262a45bf7c02310eb13e98d0e697ffcb386c029",
    "responsive-contract.json": "c0026ed3539b0b5442d9d6c188c2316b4ee39d3ca72828bbbd532d3cf53c2d33",
    "shopify-section-map.md": "727515f713d68cd361a067a8b48734a844715271928472c5dfcdff54be01ad2f",
}
GLOBAL_SETTING_TOKENS = {
    "navigation",
    "search",
    "newsletter",
    "social_links",
    "footer_menu",
    "header_menu",
}


def load(name: str) -> dict:
    path = CONTRACTS / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{name}: root must be an object")
    return data


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()
    failures: list[str] = []

    for filename, expected_hash in EXPECTED_CONTRACT_HASHES.items():
        path = CONTRACTS / filename
        try:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            fail(f"could not hash frozen contract {filename}: {exc}", failures)
            continue
        if actual_hash != expected_hash:
            fail(
                f"frozen contract hash differs for {filename}: {actual_hash}",
                failures,
            )

    editor = load("editor-schema-contract.json")
    interaction = load("interaction-contract.json")
    responsive = load("responsive-contract.json")
    ownership = load("file-ownership.json")
    migration = load("content-migration-contract.json")
    contracts = [editor, interaction, responsive, ownership, migration]

    versions = {item.get("contract_version") for item in contracts}
    if len(versions) != 1 or None in versions:
        fail(f"contract versions must match exactly: {sorted(map(str, versions))}", failures)
    statuses = {item.get("status") for item in contracts}
    allowed = {"draft", "frozen"} if args.allow_draft else {"frozen"}
    if not statuses <= allowed or len(statuses) != 1:
        fail(f"contract statuses must match and be in {sorted(allowed)}: {statuses}", failures)

    sections = editor.get("sections")
    if not isinstance(sections, list):
        fail("editor contract sections must be an array", failures)
        sections = []
    types = [item.get("type") for item in sections]
    names = [item.get("name") for item in sections]
    if types != EXPECTED_TYPES:
        fail(f"section type order mismatch: {types}", failures)
    if names != EXPECTED_NAMES:
        fail(f"section editor name order mismatch: {names}", failures)
    if any("figma" in (name or "").lower() for name in names):
        fail("editor-facing section names must not contain Figma", failures)

    for section in sections:
        settings = section.get("settings", [])
        if len(settings) != len(set(settings)):
            fail(f"{section.get('type')}: duplicate setting IDs", failures)
        forbidden = sorted(GLOBAL_SETTING_TOKENS.intersection(settings))
        if forbidden:
            fail(f"{section.get('type')}: owns global settings {forbidden}", failures)
        for block in section.get("blocks", []):
            if block.get("minimum", 0) > block.get("maximum", 0):
                fail(f"{section.get('type')}/{block.get('type')}: invalid block limits", failures)
            block_settings = block.get("settings", [])
            if block_settings and not any(key in block_settings for key in ("heading", "title", "text")):
                fail(f"{section.get('type')}/{block.get('type')}: lacks dynamic title setting", failures)

    migration_sections = migration.get("sections", {})
    if list(migration_sections) != EXPECTED_TYPES:
        fail(f"content migration section order mismatch: {list(migration_sections)}", failures)
    if migration.get("migration_policy", {}).get("preserve_current_copy") is not True:
        fail("content migration must preserve current copy", failures)
    if migration.get("migration_policy", {}).get("remove_page_owned_global_shell_content") is not True:
        fail("content migration must remove page-owned global shell content", failures)
    removed = migration.get("removed_page_owned_settings", [])
    for setting in ("search_placeholder", "newsletter_heading", "copyright_text"):
        if setting not in removed:
            fail(f"content migration does not remove page-owned global setting: {setting}", failures)

    shell = interaction.get("global_shell", {})
    if shell.get("header_section_group") != "header-group":
        fail("global header-group authority missing", failures)
    if shell.get("footer_section_group") != "footer-group":
        fail("global footer-group authority missing", failures)
    if shell.get("render_exactly_once") is not True:
        fail("global shell must render exactly once", failures)
    if shell.get("about_specific_shell_allowed") is not False:
        fail("About-specific shell must be forbidden", failures)

    search_requirements = interaction.get("predictive_search", {}).get("requirements", [])
    for phrase in ("normal GET search submission", "live product suggestions", "keyboard navigation"):
        if not any(phrase in item for item in search_requirements):
            fail(f"predictive search contract missing: {phrase}", failures)

    if responsive.get("required_viewports") != [390, 768, 1440]:
        fail("required viewports must be exactly 390, 768, 1440", failures)

    lane_paths: dict[str, set[str]] = {}
    for lane in ("sections_a", "sections_b"):
        paths = set(ownership.get(lane, {}).get("owned_paths", []))
        lane_paths[lane] = {p for p in paths if not p.startswith("focused tests")}
    overlap = lane_paths["sections_a"].intersection(lane_paths["sections_b"])
    if overlap:
        fail(f"implementation lane ownership overlaps: {sorted(overlap)}", failures)

    map_text = (CONTRACTS / "shopify-section-map.md").read_text(encoding="utf-8")
    for name in EXPECTED_NAMES:
        if name not in map_text:
            fail(f"section map missing editor name: {name}", failures)
    if "Status: FROZEN" not in map_text and not args.allow_draft:
        fail("section map is not marked FROZEN", failures)

    if failures:
        print("Contract validation failed:", file=sys.stderr)
        for message in failures:
            print(f"- {message}", file=sys.stderr)
        return 1
    print(f"Contract validation passed: {len(sections)} sections, version {next(iter(versions))}.")
    print(f"Status: {next(iter(statuses))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
