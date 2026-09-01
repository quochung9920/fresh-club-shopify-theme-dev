#!/usr/bin/env python
"""Build the immutable About Us HTML authority into a local static prototype."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FEATURE = REPO / "prototype" / "about-us"
SOURCE = FEATURE / "reference" / "about-us_1.html"
ASSET_MANIFEST = FEATURE / "notes" / "figma-asset-download-manifest.json"
WORKING = FEATURE / "working"
ASSETS = WORKING / "assets"
EXPECTED_SOURCE_SHA256 = "730247ac286a7123fcaea2459100e4905801557101aa9a25b433eddee7312329"

URL_TO_NAME = {
    "https://www.figma.com/api/mcp/asset/b814ef19-40c4-4332-8703-810723858664.png": "freshclub-logo-header.png",
    "https://www.figma.com/api/mcp/asset/72bc415d-cd17-4d54-bb61-e9bea0b711c8.png": "freshclub-value-freshness.png",
    "https://www.figma.com/api/mcp/asset/da1ed561-731c-4f03-a591-67ab8add326c.png": "freshclub-value-pricing.png",
    "https://www.figma.com/api/mcp/asset/55e879c6-13af-44df-8d0d-85a31ea36069.png": "freshclub-value-quality.png",
    "https://www.figma.com/api/mcp/asset/3e30c1b5-e1b8-42db-b624-67ee600ef818.png": "freshclub-value-local.png",
    "https://www.figma.com/api/mcp/asset/909084d5-4f69-4eaa-a9df-22d31a628f9d.png": "freshclub-about-hero-base.jpg",
    "https://www.figma.com/api/mcp/asset/b63097f3-4789-4b0e-b8f7-65e02b97fdc6.png": "freshclub-about-hero-overlay.jpg",
    "https://www.figma.com/api/mcp/asset/608d06e6-f679-427d-9888-6291f3e2473d.png": "freshclub-about-story.jpg",
    "https://www.figma.com/api/mcp/asset/429a790a-6898-4c86-890f-dd6f5b0db44a.png": "freshclub-about-cta-bg.png",
    "https://www.figma.com/api/mcp/asset/79318fa7-25a1-4d0c-a512-f09d97b6ea5c.png": "freshclub-value-ring.png",
    "https://www.figma.com/api/mcp/asset/968925ad-dcb7-4661-a90b-a39dbc2fe8f6.png": "freshclub-about-cta-decoration.png",
    "https://www.figma.com/api/mcp/asset/ee1fe1a4-ea65-4407-be2f-59f169554851.png": "freshclub-logo-footer.png",
}

FONT_CSS = """<style data-about-us-local-fonts>
@font-face { font-family: 'Lexend Deca'; src: url('./assets/lexend-deca-400.woff2') format('woff2'); font-style: normal; font-weight: 400; font-display: swap; }
@font-face { font-family: 'Lexend Deca'; src: url('./assets/lexend-deca-500.woff2') format('woff2'); font-style: normal; font-weight: 500; font-display: swap; }
@font-face { font-family: 'Lexend Deca'; src: url('./assets/lexend-deca-600.woff2') format('woff2'); font-style: normal; font-weight: 600; font-display: swap; }
@font-face { font-family: 'Lexend Deca'; src: url('./assets/lexend-deca-700.woff2') format('woff2'); font-style: normal; font-weight: 700; font-display: swap; }
@font-face { font-family: 'DM Sans'; src: url('./assets/dm-sans-600.woff2') format('woff2'); font-style: normal; font-weight: 600; font-display: swap; }
</style>"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    source_bytes = SOURCE.read_bytes()
    actual_source_hash = sha256(source_bytes)
    if actual_source_hash != EXPECTED_SOURCE_SHA256:
        raise SystemExit(
            f"Authority drift: expected {EXPECTED_SOURCE_SHA256}, got {actual_source_hash}"
        )

    manifest = json.loads(ASSET_MANIFEST.read_text(encoding="utf-8"))
    by_url = {record["source_url"]: record for record in manifest["assets"]}
    missing_urls = sorted(set(URL_TO_NAME) - set(by_url))
    if missing_urls:
        raise SystemExit(f"Asset manifest is missing source URLs: {missing_urls}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    copied = []
    for source_url, name in URL_TO_NAME.items():
        record = by_url[source_url]
        source_path = REPO / record["local_path"]
        data = source_path.read_bytes()
        if sha256(data) != record["sha256"]:
            raise SystemExit(f"Asset drift: {source_path}")
        destination = ASSETS / name
        destination.write_bytes(data)
        copied.append(
            {
                "source_url": source_url,
                "source_node_frame": record["frame"],
                "usage": record["usage"],
                "local_path": destination.relative_to(REPO).as_posix(),
                "bytes": len(data),
                "sha256": sha256(data),
                "content_type": record["content_type"],
            }
        )

    html = source_bytes.decode("utf-8")
    html = html.replace(
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link href="https://fonts.googleapis.com/css2?family=Lexend+Deca:wght@400;500;600;700&family=DM+Sans:wght@600&display=swap" rel="stylesheet">',
        FONT_CSS,
    )
    for source_url, name in URL_TO_NAME.items():
        html = html.replace(source_url, f"./assets/{name}")
    baseline_html = html
    baseline_output = WORKING / "reference-local.html"
    baseline_output.write_text(baseline_html, encoding="utf-8", newline="\n")

    html = html.replace("<body>", "<body data-about-us-root>", 1)
    html = html.replace(
        "</body>",
        '<script src="./assets/gsap-3.13.0.min.js"></script>\n'
        '<script src="./about-us.js"></script>\n'
        "</body>",
        1,
    )

    forbidden = (
        "www.figma.com/api/mcp/asset/",
        "localhost:3845",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
    )
    present_forbidden = [value for value in forbidden if value in html]
    if present_forbidden:
        raise SystemExit(f"Remote dependency remained in candidate: {present_forbidden}")

    output = WORKING / "index.html"
    output.write_text(html, encoding="utf-8", newline="\n")

    referenced = sorted(
        {
            part.split("'", 1)[0].split('"', 1)[0].split(")", 1)[0]
            for part in html.split("./assets/")[1:]
        }
    )
    missing_local = [name for name in referenced if not (ASSETS / name).is_file()]
    if missing_local:
        raise SystemExit(f"Candidate references missing local assets: {missing_local}")

    evidence = {
        "authority_sha256": actual_source_hash,
        "local_reference_path": baseline_output.relative_to(REPO).as_posix(),
        "local_reference_sha256": sha256(baseline_output.read_bytes()),
        "candidate_path": output.relative_to(REPO).as_posix(),
        "candidate_sha256": sha256(output.read_bytes()),
        "copied_figma_assets": copied,
        "referenced_local_assets": referenced,
        "missing_local_assets": missing_local,
        "forbidden_remote_dependencies": present_forbidden,
    }
    evidence_path = FEATURE / "notes" / "static-build-verification.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
