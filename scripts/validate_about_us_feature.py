#!/usr/bin/env python
"""Fail-closed validation for the Figma-derived About Us feature."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import struct
import zlib
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "prototype" / "about-us"
EXPECTED_AUTHORITY_HASH = "730247ac286a7123fcaea2459100e4905801557101aa9a25b433eddee7312329"
EXPECTED_SECTION_MARKUP_HASH = "a3747e9f8781857e167fd048f79a1f5db2d252ef140aba0cab33860db514ad3d"
EXPECTED_GENERATED_CSS_HASH = "6ca1a7e489f8873d1ce41065e8235fa068feb3a7b2b3f98f88b86c73eefae550"
REQUIRED_VIEWPORTS = {"375", "390", "768", "1440"}
REQUIRED_RUNTIME_ASSETS = {
    "about-us-figma.css",
    "about-us-figma.js",
    "gsap-3.13.0.min.js",
    "freshclub-about-hero-base.jpg",
    "freshclub-about-hero-overlay.jpg",
    "freshclub-about-story.jpg",
    "freshclub-about-cta-bg.png",
    "freshclub-about-cta-decoration.png",
    "freshclub-logo-header.png",
    "freshclub-logo-footer.png",
    "freshclub-value-ring.png",
    "freshclub-value-freshness.png",
    "freshclub-value-pricing.png",
    "freshclub-value-quality.png",
    "freshclub-value-local.png",
    "lexend-deca-400.woff2",
    "lexend-deca-500.woff2",
    "lexend-deca-600.woff2",
    "lexend-deca-700.woff2",
    "dm-sans-600.woff2",
}
EXPECTED_RUNTIME_PATHS = {f"assets/{filename}" for filename in REQUIRED_RUNTIME_ASSETS}
COMPARISON_FIELDS = {
    "referenceDimensions",
    "candidateDimensions",
    "equalDimensions",
    "diffBoundingBox",
    "meanPerChannelDelta",
    "pixelIdentical",
    "maxMeanChannelDelta",
    "withinTolerance",
}
RUNTIME_TEXT_FILES = {
    ROOT / "assets" / "about-us-figma.css",
    ROOT / "assets" / "about-us-figma.js",
    ROOT / "sections" / "about-us-figma.liquid",
    ROOT / "templates" / "page.about-us.json",
    FEATURE / "working" / "index.html",
}
FORBIDDEN_RUNTIME_FRAGMENTS = (
    "www.figma.com/api/mcp/asset/",
    "localhost:3845",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def exact_css_rule_declarations(css: str, selector: str) -> list[dict[str, str]]:
    """Return every declaration map for one exact selector."""
    without_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    pattern = re.compile(
        rf"(?m)(?<![^}}\n])\s*{re.escape(selector)}\s*\{{([^{{}}]*)\}}"
    )
    matches = pattern.findall(without_comments)
    if not matches:
        raise ValueError(f"expected at least one exact CSS rule for {selector!r}")
    rules: list[dict[str, str]] = []
    for body in matches:
        declarations: dict[str, str] = {}
        for declaration in body.split(";"):
            if not declaration.strip():
                continue
            if ":" not in declaration:
                raise ValueError(f"malformed declaration in {selector!r}: {declaration!r}")
            name, value = declaration.split(":", 1)
            normalized_name = name.strip().lower()
            if normalized_name in declarations:
                raise ValueError(f"duplicate declaration {normalized_name!r} in {selector!r}")
            declarations[normalized_name] = value.strip().lower()
        rules.append(declarations)
    return rules


def repo_path(relative: object) -> Path:
    """Resolve a manifest path while rejecting absolute/traversal/symlink escapes."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"invalid repository-relative path: {relative!r}")
    lexical = Path(relative)
    if lexical.is_absolute() or any(part in {"", ".", ".."} for part in lexical.parts):
        raise ValueError(f"unsafe repository-relative path: {relative!r}")
    lexical_path = ROOT
    for part in lexical.parts:
        lexical_path /= part
        try:
            metadata = lexical_path.lstat()
        except FileNotFoundError:
            raise ValueError(f"repository evidence path is missing: {relative!r}") from None
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"repository evidence path contains a symlink: {relative!r}")
    resolved = (ROOT / lexical).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"path escapes repository: {relative!r}")
    return resolved


def file_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    """Return fields that must remain stable for one coherent evidence read."""
    return (
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


class CtaDecorationParser(HTMLParser):
    """Fail-closed structural inventory for CTA decoration markup."""

    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
    SVG_SELF_CLOSING_ELEMENTS = {
        "circle", "ellipse", "line", "path", "polygon", "polyline", "rect",
        "stop", "use",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, object]] = []
        self.asset_references = 0
        self.parents: list[dict[str, object]] = []
        self.errors: list[str] = []

    @staticmethod
    def _is_decoration_class(tokens: list[str]) -> bool:
        return any(
            token == "fc-cta-deco" or token.startswith("fc-cta-deco--")
            for token in tokens
        )

    def _handle_open(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
        *,
        self_closing: bool,
    ) -> None:
        names = [name for name, _value in attrs]
        if len(names) != len(set(names)):
            self.errors.append(f"duplicate attributes on <{tag}>")
        attributes = dict(attrs)
        class_tokens = (attributes.get("class") or "").split()
        is_decoration_parent = tag == "div" and self._is_decoration_class(class_tokens)
        if is_decoration_parent and len(class_tokens) != len(set(class_tokens)):
            self.errors.append("duplicate CTA decoration class token")

        parent_index: int | None = None
        if is_decoration_parent:
            parent_index = len(self.parents)
            self.parents.append(
                {
                    "attrs": attributes,
                    "class_tokens": class_tokens,
                    "direct_images": [],
                    "closed": False,
                    "self_closing": self_closing,
                }
            )

        if tag == "img":
            source = attributes.get("src") or ""
            if "freshclub-about-cta-decoration.png" in source:
                self.asset_references += 1
            if self.stack:
                direct_parent = self.stack[-1].get("decoration_index")
                if isinstance(direct_parent, int):
                    images = self.parents[direct_parent]["direct_images"]
                    assert isinstance(images, list)
                    images.append(
                        {
                            "attrs": attributes,
                            "duplicate_attributes": len(names) != len(set(names)),
                            "self_closing": self_closing,
                        }
                    )

        if self_closing:
            if tag not in self.SVG_SELF_CLOSING_ELEMENTS:
                self.errors.append(f"disallowed self-closing <{tag}/> form")
            return
        if tag not in self.VOID_ELEMENTS:
            self.stack.append({"tag": tag, "decoration_index": parent_index})

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_open(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_open(tag, attrs, self_closing=True)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1]["tag"] != tag:
            expected = self.stack[-1]["tag"] if self.stack else "none"
            self.errors.append(f"mismatched </{tag}>; expected </{expected}>")
            return
        entry = self.stack.pop()
        parent_index = entry.get("decoration_index")
        if isinstance(parent_index, int):
            self.parents[parent_index]["closed"] = True

    def finish(self) -> None:
        self.close()
        if self.stack:
            unclosed = ", ".join(str(entry["tag"]) for entry in self.stack)
            self.errors.append(f"unclosed markup: {unclosed}")


def read_png_rgb(path: Path) -> tuple[int, int, bytes]:
    """Decode the committed 8-bit, non-interlaced RGB PNG evidence."""
    relative = path.relative_to(ROOT).as_posix()
    path = repo_path(relative)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"PNG evidence is not a regular file: {relative}")
    if before.st_size > 10_000_000:
        raise ValueError(f"PNG file exceeds evidence size limit: {relative}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened_before = os.fstat(descriptor)
        if not stat.S_ISREG(opened_before.st_mode) or opened_before.st_size > 10_000_000:
            raise ValueError(f"PNG file exceeds evidence size limit: {relative}")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(10_000_001)
            if len(data) != opened_before.st_size or stream.read(1):
                raise ValueError(f"PNG changed or exceeded the read limit: {relative}")
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = path.lstat()
    signatures = {
        file_signature(before),
        file_signature(opened_before),
        file_signature(opened_after),
        file_signature(after),
    }
    if stat.S_ISLNK(after.st_mode) or len(signatures) != 1:
        raise ValueError(f"PNG path changed while reading: {relative}")
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not a PNG: {path.relative_to(ROOT)}")
    cursor = 8
    ihdr: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    saw_end = False
    while cursor < len(data):
        if cursor + 12 > len(data):
            raise ValueError(f"truncated PNG chunk: {path.relative_to(ROOT)}")
        length = struct.unpack(">I", data[cursor : cursor + 4])[0]
        kind = data[cursor + 4 : cursor + 8]
        payload_start = cursor + 8
        payload_end = payload_start + length
        crc_end = payload_end + 4
        if crc_end > len(data):
            raise ValueError(f"truncated PNG payload: {path.relative_to(ROOT)}")
        payload = data[payload_start:payload_end]
        expected_crc = struct.unpack(">I", data[payload_end:crc_end])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            raise ValueError(f"invalid PNG CRC: {path.relative_to(ROOT)}")
        if kind == b"IHDR":
            if ihdr is not None or length != 13:
                raise ValueError(f"invalid PNG IHDR: {path.relative_to(ROOT)}")
            ihdr = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            if ihdr is None:
                raise ValueError(f"PNG IDAT precedes IHDR: {path.relative_to(ROOT)}")
            if len(compressed) + len(payload) > 8_000_000:
                raise ValueError(f"PNG IDAT exceeds evidence size limit: {path.relative_to(ROOT)}")
            compressed.extend(payload)
        elif kind == b"IEND":
            if length != 0:
                raise ValueError(f"PNG IEND payload must be empty: {path.relative_to(ROOT)}")
            saw_end = True
            if crc_end != len(data):
                raise ValueError(f"trailing PNG bytes: {path.relative_to(ROOT)}")
        cursor = crc_end
    if ihdr is None or not saw_end:
        raise ValueError(f"incomplete PNG: {path.relative_to(ROOT)}")
    width, height, bit_depth, color_type, compression, filtering, interlace = ihdr
    if width <= 0 or height <= 0 or width > 2000 or height > 6000 or width * height > 12_000_000:
        raise ValueError(f"unsafe PNG dimensions: {path.relative_to(ROOT)}")
    if (bit_depth, color_type, compression, filtering, interlace) != (8, 2, 0, 0, 0):
        raise ValueError(f"unsupported PNG format: {path.relative_to(ROOT)}")
    stride = width * 3
    expected_inflated_size = height * (stride + 1)
    decompressor = zlib.decompressobj()
    inflated = decompressor.decompress(bytes(compressed), expected_inflated_size + 1)
    if len(inflated) > expected_inflated_size or decompressor.unconsumed_tail:
        raise ValueError(f"PNG decompression exceeds declared dimensions: {path.relative_to(ROOT)}")
    if not decompressor.eof or decompressor.unused_data:
        raise ValueError(f"invalid or trailing PNG compressed stream: {path.relative_to(ROOT)}")
    inflated += decompressor.flush(expected_inflated_size + 1 - len(inflated))
    if len(inflated) != expected_inflated_size:
        raise ValueError(f"invalid PNG scanline size: {path.relative_to(ROOT)}")
    pixels = bytearray(width * height * 3)
    previous = bytearray(stride)
    source_offset = 0
    target_offset = 0
    for _ in range(height):
        filter_type = inflated[source_offset]
        source_offset += 1
        row = bytearray(inflated[source_offset : source_offset + stride])
        source_offset += stride
        if filter_type not in {0, 1, 2, 3, 4}:
            raise ValueError(f"unsupported PNG filter: {path.relative_to(ROOT)}")
        for index in range(stride):
            left = row[index - 3] if index >= 3 else 0
            above = previous[index]
            upper_left = previous[index - 3] if index >= 3 else 0
            if filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                estimate = left + above - upper_left
                distance_left = abs(estimate - left)
                distance_above = abs(estimate - above)
                distance_upper_left = abs(estimate - upper_left)
                predictor = (
                    left
                    if distance_left <= distance_above and distance_left <= distance_upper_left
                    else above if distance_above <= distance_upper_left else upper_left
                )
            else:
                predictor = 0
            row[index] = (row[index] + predictor) & 0xFF
        pixels[target_offset : target_offset + stride] = row
        target_offset += stride
        previous = row
    return width, height, bytes(pixels)


def recompute_comparison(
    reference_path: Path, candidate_path: Path, diff_path: Path
) -> dict[str, object]:
    ref_width, ref_height, reference = read_png_rgb(reference_path)
    candidate_width, candidate_height, candidate = read_png_rgb(candidate_path)
    diff_width, diff_height, committed_diff = read_png_rgb(diff_path)
    if (ref_width, ref_height) != (candidate_width, candidate_height):
        return {
            "referenceDimensions": [ref_width, ref_height],
            "candidateDimensions": [candidate_width, candidate_height],
            "equalDimensions": False,
        }
    if (diff_width, diff_height) != (ref_width, ref_height):
        raise ValueError(f"difference image dimensions differ: {diff_path.relative_to(ROOT)}")
    sums = [0, 0, 0]
    min_x = ref_width
    min_y = ref_height
    max_x = -1
    max_y = -1
    calculated_diff = bytearray(len(reference))
    for offset in range(0, len(reference), 3):
        changed = False
        for channel in range(3):
            delta = abs(reference[offset + channel] - candidate[offset + channel])
            calculated_diff[offset + channel] = delta
            sums[channel] += delta
            changed = changed or delta != 0
        if changed:
            pixel = offset // 3
            x = pixel % ref_width
            y = pixel // ref_width
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if bytes(calculated_diff) != committed_diff:
        raise ValueError(f"difference image bytes are not the pixel delta: {diff_path.relative_to(ROOT)}")
    pixel_count = ref_width * ref_height
    means = [round(total / pixel_count, 6) for total in sums]
    identical = max_x < 0
    return {
        "referenceDimensions": [ref_width, ref_height],
        "candidateDimensions": [candidate_width, candidate_height],
        "equalDimensions": True,
        "diffBoundingBox": None if identical else [min_x, min_y, max_x + 1, max_y + 1],
        "meanPerChannelDelta": means,
        "pixelIdentical": identical,
    }


def main() -> int:
    errors: list[str] = []
    visual_residuals: list[str] = []
    section_schema: dict[str, object] = {}

    authority = FEATURE / "reference" / "about-us_1.html"
    if not authority.is_file() or sha256(authority) != EXPECTED_AUTHORITY_HASH:
        fail(errors, "immutable HTML authority is missing or has drifted")

    reference_manifest_path = FEATURE / "notes" / "reference-manifest.json"
    try:
        reference_manifest = json.loads(reference_manifest_path.read_text(encoding="utf-8"))
        authority_data = reference_manifest["authority"]
        if authority_data.get("desktop_node") != "81154:408":
            fail(errors, "desktop Figma authority must be node 81154:408")
        if authority_data.get("mobile_node") != "81177:209":
            fail(errors, "mobile Figma authority must be node 81177:209")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        fail(errors, f"invalid reference manifest: {exc}")

    for filename in sorted(REQUIRED_RUNTIME_ASSETS):
        if not (ROOT / "assets" / filename).is_file():
            fail(errors, f"missing runtime asset: assets/{filename}")

    asset_evidence_path = FEATURE / "notes" / "theme-asset-build-verification.json"
    try:
        asset_evidence = json.loads(asset_evidence_path.read_text(encoding="utf-8"))
        expected_evidence_fields = {
            "authority_sha256",
            "scoped_classes",
            "remaining_remote_dependencies",
            "unscoped_css_classes",
            "liquid_css_fixture",
            "installed",
        }
        if set(asset_evidence) != expected_evidence_fields:
            raise ValueError("theme asset evidence has unknown or missing top-level fields")
        if asset_evidence["authority_sha256"] != EXPECTED_AUTHORITY_HASH:
            fail(errors, "theme asset evidence has the wrong authority hash")
        if (
            not isinstance(asset_evidence["scoped_classes"], int)
            or isinstance(asset_evidence["scoped_classes"], bool)
            or asset_evidence["scoped_classes"] <= 0
        ):
            fail(errors, "theme asset evidence has an invalid scoped class count")
        if asset_evidence["liquid_css_fixture"] != "prototype/about-us/working/liquid-css-fixture.html":
            fail(errors, "theme asset evidence has the wrong Liquid fixture path")
        repo_path(asset_evidence["liquid_css_fixture"])
        installed_items = asset_evidence["installed"]
        if not isinstance(installed_items, list):
            raise TypeError("installed runtime inventory must be a list")
        installed_paths = [item["file"] for item in installed_items]
        if len(installed_paths) != len(set(installed_paths)):
            fail(errors, "runtime asset evidence contains duplicate paths")
        if set(installed_paths) != EXPECTED_RUNTIME_PATHS:
            fail(
                errors,
                "runtime asset evidence inventory differs: "
                f"expected={sorted(EXPECTED_RUNTIME_PATHS)}, actual={sorted(set(installed_paths))}",
            )
        installed = {item["file"]: item for item in installed_items}
        for relative, item in installed.items():
            path = repo_path(relative)
            if set(item) != {"file", "bytes", "sha256"}:
                fail(errors, f"runtime asset evidence has unknown fields: {relative}")
                continue
            if not path.is_file():
                fail(errors, f"evidence references missing file: {relative}")
                continue
            if (
                not isinstance(item["bytes"], int)
                or isinstance(item["bytes"], bool)
                or not isinstance(item["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                or path.stat().st_size != item["bytes"]
                or sha256(path) != item["sha256"]
            ):
                fail(errors, f"runtime asset differs from build evidence: {relative}")
        if asset_evidence.get("remaining_remote_dependencies") != []:
            fail(errors, "theme asset build evidence reports remote dependencies")
        if asset_evidence.get("unscoped_css_classes") != []:
            fail(errors, "theme asset build evidence reports unscoped CSS classes")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        fail(errors, f"invalid theme asset evidence: {exc}")

    for path in sorted(RUNTIME_TEXT_FILES):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            fail(errors, f"could not read runtime file {path.relative_to(ROOT)}: {exc}")
            continue
        for fragment in FORBIDDEN_RUNTIME_FRAGMENTS:
            if fragment in text:
                fail(errors, f"forbidden remote runtime dependency in {path.relative_to(ROOT)}: {fragment}")

    try:
        theme_css_path = ROOT / "assets" / "about-us-figma.css"
        fixture_css_path = FEATURE / "working" / "assets" / "about-us-figma.css"
        theme_css_hash = sha256(theme_css_path)
        fixture_css_hash = sha256(fixture_css_path)
        if theme_css_hash != EXPECTED_GENERATED_CSS_HASH:
            fail(
                errors,
                f"generated About Us CSS hash differs: {theme_css_hash}",
            )
        if fixture_css_hash != EXPECTED_GENERATED_CSS_HASH:
            fail(
                errors,
                f"generated fixture CSS hash differs: {fixture_css_hash}",
            )
        theme_css = theme_css_path.read_text(encoding="utf-8")
        malformed_fragments = (
            "story-.fc-about-root",
            "ct.fc-about-root",
            ".fc-footer-nav .fc-about-root",
            ".fc-nav-desktop .fc-about-root",
            ".fc-social .fc-about-root",
        )
        for fragment in malformed_fragments:
            if fragment in theme_css:
                fail(errors, f"malformed generated CSS selector remains: {fragment}")
        for line_number, line in enumerate(theme_css.splitlines(), start=1):
            stripped = line.lstrip()
            if "{" not in stripped or stripped.startswith(("@", "/*", "*")):
                continue
            selector = stripped.split("{", 1)[0]
            if "freshclub-about-us[data-section-id]" not in selector:
                fail(errors, f"unscoped theme CSS selector at line {line_number}: {selector}")
        for interaction_contract in (":focus-visible", ":focus-within", ":active", ":hover"):
            if interaction_contract not in theme_css:
                fail(errors, f"missing interaction style contract: {interaction_contract}")
        required_heading_colors = {
            "freshclub-about-us[data-section-id] .fc-cta-title h2": "#fff",
            "freshclub-about-us[data-section-id] .fc-newsletter h4": "#fff",
        }
        for selector, expected_color in required_heading_colors.items():
            try:
                rules = exact_css_rule_declarations(theme_css, selector)
            except ValueError as exc:
                fail(errors, str(exc))
                continue
            declared_colors = [rule["color"] for rule in rules if "color" in rule]
            if expected_color not in declared_colors or any(
                color != expected_color for color in declared_colors
            ):
                fail(
                    errors,
                    f"{selector} must explicitly set color {expected_color} without conflicting color declarations",
                )
        for newsletter_selector in (".fc-newsletter h4", ".fc-newsletter {"):
            if newsletter_selector not in theme_css:
                fail(errors, f"missing valid newsletter CSS selector: {newsletter_selector}")
        for baseline_compatibility_rule in (
            "freshclub-about-us[data-section-id] .fc-photo-frame { display: block; }",
            "freshclub-about-us[data-section-id] .fc-header-spacer { display: block; }",
            "freshclub-about-us[data-section-id] .fc-story-panel { display: block; }",
        ):
            if baseline_compatibility_rule not in theme_css:
                fail(errors, f"missing baseline empty-element compatibility rule: {baseline_compatibility_rule}")
    except (OSError, UnicodeDecodeError) as exc:
        fail(errors, f"could not validate generated About Us CSS: {exc}")

    section_path = ROOT / "sections" / "about-us-figma.liquid"
    try:
        section = section_path.read_text(encoding="utf-8")
        if 'class="fc-newsletter"' not in section:
            fail(errors, "missing valid newsletter class in About Us Liquid")
        markup = section.split("{% schema %}", 1)[0]
        markup_hash = hashlib.sha256(markup.encode("utf-8")).hexdigest()
        if markup_hash != EXPECTED_SECTION_MARKUP_HASH:
            fail(
                errors,
                f"About Us Liquid markup hash differs: {markup_hash}",
            )
        expected_footer_logo = (
            '<img class="fc-logo-footer" '
            'src="{{ \'freshclub-logo-footer.png\' | asset_url }}" '
            'alt="FreshClub" width="169" height="41" loading="eager">'
        )
        if markup.count(expected_footer_logo) != 1:
            fail(errors, "About Us footer logo must load eagerly exactly once")
        decoration_parser = CtaDecorationParser()
        decoration_parser.feed(markup)
        decoration_parser.finish()
        if re.search(r"</\s*[A-Za-z][^>]*?/\s*>", markup):
            decoration_parser.errors.append("malformed self-closing end tag")
        expected_src = "{{ 'freshclub-about-cta-decoration.png' | asset_url }}"
        expected_image_attributes = {
            "src": expected_src,
            "alt": "",
            "width": "206",
            "height": "165",
            "loading": "eager",
        }
        expected_parents = {
            "fc-cta-deco fc-cta-deco--left": {
                "class": "fc-cta-deco fc-cta-deco--left",
                "aria-hidden": "true",
            },
            "fc-cta-deco fc-cta-deco--right": {
                "class": "fc-cta-deco fc-cta-deco--right",
                "aria-hidden": "true",
            },
        }
        seen_parent_classes: set[str] = set()
        decoration_valid = (
            not decoration_parser.errors
            and section.count("freshclub-about-cta-decoration.png") == 2
            and decoration_parser.asset_references == 2
            and len(decoration_parser.parents) == 2
        )
        for parent in decoration_parser.parents:
            attributes = parent.get("attrs")
            direct_images = parent.get("direct_images")
            if not isinstance(attributes, dict) or not isinstance(direct_images, list):
                decoration_valid = False
                continue
            class_value = attributes.get("class")
            if not isinstance(class_value, str) or class_value not in expected_parents:
                decoration_valid = False
                continue
            seen_parent_classes.add(class_value)
            if (
                attributes != expected_parents[class_value]
                or parent.get("closed") is not True
                or parent.get("self_closing") is not False
                or len(direct_images) != 1
            ):
                decoration_valid = False
                continue
            image = direct_images[0]
            if (
                not isinstance(image, dict)
                or image.get("attrs") != expected_image_attributes
                or image.get("duplicate_attributes") is not False
                or image.get("self_closing") is not False
            ):
                decoration_valid = False
        if seen_parent_classes != set(expected_parents):
            decoration_valid = False
        if not decoration_valid:
            details = "; ".join(decoration_parser.errors[:5])
            fail(
                errors,
                "CTA decoration image structure or eager-loading contract is invalid"
                + (f": {details}" if details else ""),
            )
        schema_match = re.search(r"{% schema %}\s*(.*?)\s*{% endschema %}", section, re.DOTALL)
        if not schema_match:
            fail(errors, "About Us section schema is missing")
        else:
            section_schema = json.loads(schema_match.group(1))
            if len(section_schema.get("settings", [])) > 50:
                fail(errors, "About Us section exceeds Shopify's 50-setting limit")
            block_limits = {
                item["type"]: item.get("limit") for item in section_schema.get("blocks", [])
            }
            if block_limits != {"value": 4, "stat": 4, "step": 4}:
                fail(errors, f"unexpected About Us block limits: {block_limits}")
        for contract in (
            'data-section-id="{{ section.id | escape }}"',
            'aria-controls="AboutUsMenu-{{ section.id | escape }}"',
            'class="fc-mobile-nav"',
            "shopify:section:load",
            "shopify:section:unload",
            "prefers-reduced-motion",
            "setupMenu",
            "setMenuOpen",
        ):
            combined = section + (ROOT / "assets" / "about-us-figma.js").read_text(encoding="utf-8")
            if contract not in combined:
                fail(errors, f"missing section lifecycle contract: {contract}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        fail(errors, f"invalid About Us section/schema: {exc}")

    try:
        template = json.loads((ROOT / "templates" / "page.about-us.json").read_text(encoding="utf-8"))
        if set(template) != {"sections", "order"}:
            fail(errors, f"About Us template has unknown top-level keys: {sorted(set(template) - {'sections', 'order'})}")
        sections = template.get("sections", {})
        if set(sections) != {"about_us_figma"}:
            fail(errors, f"About Us template section inventory differs: {sorted(sections)}")
        if template.get("order") != ["about_us_figma"]:
            fail(errors, "About Us template must contain only the Figma section")
        feature_section = sections.get("about_us_figma", {})
        if set(feature_section) != {"type", "blocks", "block_order", "settings"}:
            fail(errors, "About Us template section has unknown or missing keys")
        if feature_section.get("type") != "about-us-figma":
            fail(errors, "About Us template has the wrong section type")
        blocks = feature_section.get("blocks", {})
        block_order = feature_section.get("block_order", [])
        if (
            not isinstance(block_order, list)
            or len(block_order) != len(set(block_order))
            or set(block_order) != set(blocks)
            or len(block_order) != len(blocks)
        ):
            fail(errors, "About Us template block_order is not a unique closed inventory")
        block_types = Counter(
            block.get("type") for block in blocks.values()
        )
        if block_types != Counter({"value": 4, "stat": 4, "step": 4}):
            fail(errors, f"About Us template block composition is wrong: {dict(block_types)}")
        allowed_section_settings = {
            item["id"] for item in section_schema.get("settings", []) if "id" in item
        }
        actual_section_settings = feature_section.get("settings", {})
        unknown_section_settings = set(actual_section_settings) - allowed_section_settings
        if unknown_section_settings:
            fail(errors, f"About Us template has unknown section settings: {sorted(unknown_section_settings)}")
        allowed_block_settings = {
            item["type"]: {setting["id"] for setting in item.get("settings", [])}
            for item in section_schema.get("blocks", [])
        }
        for block_id, block in blocks.items():
            if set(block) != {"type", "settings"}:
                fail(errors, f"About Us template block has unknown or missing keys: {block_id}")
                continue
            block_type = block.get("type")
            if block_type not in allowed_block_settings:
                fail(errors, f"About Us template has unknown block type: {block_id}")
                continue
            unknown_block_settings = set(block.get("settings", {})) - allowed_block_settings[block_type]
            if unknown_block_settings:
                fail(
                    errors,
                    f"About Us template block {block_id} has unknown settings: {sorted(unknown_block_settings)}",
                )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        fail(errors, f"invalid About Us JSON template: {exc}")

    try:
        layout = (ROOT / "layout" / "theme.liquid").read_text(encoding="utf-8")
        if "use_about_us_figma_shell" not in layout or "template.suffix == 'about-us'" not in layout:
            fail(errors, "theme layout does not isolate the About Us custom header/footer")
    except (OSError, UnicodeDecodeError) as exc:
        fail(errors, f"could not validate theme layout: {exc}")

    if errors:
        print("About Us feature validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    visual_path = FEATURE / "notes" / "visual" / "visual-results.json"
    try:
        visual = json.loads(visual_path.read_text(encoding="utf-8"))
        if set(visual) != {"captures", "comparisons", "liquidFixtureComparisons"}:
            raise ValueError("visual evidence has unknown or missing top-level fields")
        expected_capture_paths = {
            f"prototype/about-us/notes/visual/{kind}-{viewport}.png"
            for viewport in REQUIRED_VIEWPORTS
            for kind in ("reference", "candidate", "liquid-fixture")
        }
        captures = visual["captures"]
        if not isinstance(captures, list):
            raise TypeError("visual captures must be a list")
        for capture in captures:
            if not isinstance(capture, dict):
                raise TypeError("visual capture entries must be objects")
            if set(capture) != {"screenshot", "screenshotBytes", "screenshotSha256"}:
                raise ValueError("visual capture has unknown or unverifiable fields")
        capture_paths = [capture["screenshot"] for capture in captures]
        if len(capture_paths) != len(set(capture_paths)):
            raise ValueError("visual evidence contains duplicate captures")
        if set(capture_paths) != expected_capture_paths:
            raise ValueError(
                "visual capture inventory differs: "
                f"expected={sorted(expected_capture_paths)}, actual={sorted(set(capture_paths))}"
            )
        comparisons = visual["comparisons"]
        if set(comparisons) != REQUIRED_VIEWPORTS:
            raise ValueError(f"visual evidence viewports differ: {sorted(comparisons)}")
        liquid_comparisons = visual["liquidFixtureComparisons"]
        if set(liquid_comparisons) != REQUIRED_VIEWPORTS:
            raise ValueError(f"Liquid CSS fixture viewports differ: {sorted(liquid_comparisons)}")
        visual_directory = FEATURE / "notes" / "visual"
        for viewport in sorted(REQUIRED_VIEWPORTS, key=int):
            for comparison_name, candidate_prefix, diff_prefix, residual_prefix in (
                ("comparisons", "candidate", "diff", ""),
                (
                    "liquidFixtureComparisons",
                    "liquid-fixture",
                    "liquid-fixture-diff",
                    "Liquid fixture ",
                ),
            ):
                recorded = visual[comparison_name][viewport]
                if set(recorded) != COMPARISON_FIELDS:
                    fail(errors, f"visual comparison fields differ for {comparison_name} at {viewport}px")
                    continue
                threshold = recorded["maxMeanChannelDelta"]
                if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or threshold != 0.005:
                    fail(errors, f"visual threshold differs for {comparison_name} at {viewport}px")
                    continue
                recomputed = recompute_comparison(
                    visual_directory / f"reference-{viewport}.png",
                    visual_directory / f"{candidate_prefix}-{viewport}.png",
                    visual_directory / f"{diff_prefix}-{viewport}.png",
                )
                recomputed["maxMeanChannelDelta"] = threshold
                recomputed["withinTolerance"] = bool(
                    recomputed["equalDimensions"]
                    and max(recomputed.get("meanPerChannelDelta", [float("inf")])) <= threshold
                )
                if recorded != recomputed:
                    fail(errors, f"visual comparison does not match PNG bytes for {comparison_name} at {viewport}px")
                    continue
                if not recomputed["equalDimensions"]:
                    fail(errors, f"visual dimensions differ for {comparison_name} at {viewport}px")
                if not recomputed["withinTolerance"]:
                    fail(errors, f"visual delta exceeds tolerance for {comparison_name} at {viewport}px")
                if not recomputed["pixelIdentical"]:
                    visual_residuals.append(
                        f"{residual_prefix}{viewport}px={recomputed['meanPerChannelDelta']}"
                    )
        for capture in captures:
            screenshot = repo_path(capture["screenshot"])
            width, _, _ = read_png_rgb(screenshot)
            expected_viewport = int(Path(capture["screenshot"]).stem.rsplit("-", 1)[1])
            if width != expected_viewport:
                fail(errors, f"visual capture viewport differs: {capture['screenshot']}")
            if (
                not screenshot.is_file()
                or not isinstance(capture["screenshotBytes"], int)
                or isinstance(capture["screenshotBytes"], bool)
                or not isinstance(capture["screenshotSha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", capture["screenshotSha256"])
                or screenshot.stat().st_size != capture["screenshotBytes"]
                or sha256(screenshot) != capture["screenshotSha256"]
            ):
                fail(errors, f"visual screenshot missing or changed: {capture['screenshot']}")
    except (OSError, KeyError, TypeError, ValueError, zlib.error, json.JSONDecodeError) as exc:
        fail(errors, f"invalid visual evidence: {exc}")

    if errors:
        print("About Us feature validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("About Us feature validation passed")
    print(f"Runtime assets: {len(REQUIRED_RUNTIME_ASSETS)}")
    print(f"Responsive visual anchors: {len(REQUIRED_VIEWPORTS)}")
    if visual_residuals:
        print("Static candidate residual mean RGB deltas: " + ", ".join(visual_residuals))
    else:
        print("Static candidate pixel-identical: 375/390/768/1440")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
