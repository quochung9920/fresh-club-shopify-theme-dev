from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECTION_SPECS = {
    "fc-about-hero": {
        "name": "About — Hero",
        "settings": [("heading", "inline_richtext"), ("text", "textarea"), ("image", "image_picker"), ("image_alt", "text")],
        "block_type": "button",
        "block_name": "Action",
        "block_settings": [("heading", "text"), ("link", "url"), ("style", "select")],
        "preset_keys": {"heading", "link", "style"},
        "max_blocks": 2,
        "minimum": 0,
        "css": "fc-about-hero.css",
    },
    "fc-about-values": {
        "name": "About — Values",
        "settings": [],
        "block_type": "value_card",
        "block_name": "Value card",
        "block_settings": [("icon", "image_picker"), ("heading", "text"), ("text", "textarea")],
        "preset_keys": {"heading", "text"},
        "max_blocks": 4,
        "minimum": 1,
        "css": "fc-about-values.css",
    },
    "fc-about-metrics": {
        "name": "About — Metrics",
        "settings": [("eyebrow", "text")],
        "block_type": "metric",
        "block_name": "Metric",
        "block_settings": [("value", "text"), ("heading", "text")],
        "preset_keys": {"value", "heading"},
        "max_blocks": 4,
        "minimum": 1,
        "css": "fc-about-metrics.css",
    },
}

PRODUCTION_SHA256 = {
    "sections/fc-about-hero.liquid": "2de7aec09c3f3b316e30fd85b955bf0b770849486ef3b548f2e2d6e7b67d3800",
    "sections/fc-about-values.liquid": "54f9a924c2f424759f19fa2bb35de20e962a34aaec610d6b3b1d608fd63ec9e5",
    "sections/fc-about-metrics.liquid": "2463b53c5ff44fc2f1346521976e2d278b61f1a1eae4db944b09069448f93f3f",
    "assets/fc-about-hero.css": "2227d0641bed28fe5426abafb11f1a337327750c57f7ea5d7be6ec1ecb136f4e",
    "assets/fc-about-values.css": "c6bde7720e273c194500d0c0e4725ffb100bd1bc0d82195c209e74432ed95ca3",
    "assets/fc-about-metrics.css": "5e3dec29c1e3c0a5530a19b9f3de7348892e642b99a64abaa332ab70f59ed025",
}

FORBIDDEN_LIQUID = (
    "fc-site-header",
    "fc-site-footer",
    "fc-search-field",
    "fc-btn",
    "gsap",
    "predictive-search",
    "newsletter",
)

SETTING_KEYS = {
    "image_picker": {"type", "id", "label"},
    "url": {"type", "id", "label"},
    "text": {"type", "id", "label", "default"},
    "textarea": {"type", "id", "label", "default"},
    "inline_richtext": {"type", "id", "label", "default"},
    "select": {"type", "id", "label", "options", "default"},
}


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def schema_from(text: str, path: Path, failures: list[str]) -> dict:
    matches = re.findall(r"{%\s*schema\s*%}(.*?){%\s*endschema\s*%}", text, re.S)
    if len(matches) != 1:
        fail(f"{path.name}: exactly one schema block is required", failures)
        return {}
    try:
        data = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        fail(f"{path.name}: invalid schema JSON: {exc}", failures)
        return {}
    if not isinstance(data, dict):
        fail(f"{path.name}: schema root must be an object", failures)
        return {}
    return data


def validate_setting_inventory(settings: object, expected: list[tuple[str, str]], label: str, failures: list[str]) -> None:
    if not isinstance(settings, list) or len(settings) != len(expected):
        fail(f"{label}: setting count differs from contract", failures)
        return
    actual = []
    for index, item in enumerate(settings):
        if not isinstance(item, dict):
            fail(f"{label}: setting {index} must be an object", failures)
            continue
        setting_type = item.get("type")
        setting_id = item.get("id")
        actual.append((setting_id, setting_type))
        allowed_keys = SETTING_KEYS.get(setting_type)
        if allowed_keys is None or set(item) != allowed_keys:
            fail(f"{label}: setting {setting_id!r} has unknown/missing fields for type {setting_type!r}", failures)
        if setting_type == "select":
            options = item.get("options")
            if not isinstance(options, list) or not options or any(not isinstance(option, dict) or set(option) != {"value", "label"} for option in options):
                fail(f"{label}: select {setting_id!r} has an invalid option inventory", failures)
    if actual != expected:
        fail(f"{label}: setting IDs/types/order differ from contract", failures)


def block_case_inventory(liquid: str) -> tuple[list[str], bool, str] | None:
    token_re = re.compile(r"{%-?\s*(case\s+([^%]+?)|when\s+['\"]([^'\"]+)['\"]|else\b|endcase\b)\s*-?%}", re.S)
    tokens = list(token_re.finditer(liquid))
    start = next((index for index, token in enumerate(tokens) if re.fullmatch(r"case\s+block\.type", token.group(1).strip())), None)
    if start is None:
        return None
    depth = 0
    known: list[str] = []
    top_else = False
    body_start = tokens[start].end()
    for token in tokens[start:]:
        directive = token.group(1).strip()
        if directive.startswith("case "):
            depth += 1
        elif directive.startswith("when ") and depth == 1:
            known.append(token.group(3))
        elif directive == "else" and depth == 1:
            top_else = True
        elif directive == "endcase":
            depth -= 1
            if depth == 0:
                return known, top_else, liquid[body_start:token.start()]
    return known, True, liquid[body_start:]


def css_selectors(css: str) -> list[str]:
    clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    selectors: list[str] = []
    for match in re.finditer(r"([^{}]+)\{", clean):
        prelude = match.group(1).strip()
        if not prelude or prelude.startswith("@") or prelude in {"from", "to"} or prelude.endswith("%"):
            continue
        selectors.extend(part.strip() for part in prelude.split(",") if part.strip())
    return selectors


def validate_schema(schema: dict, section_type: str, spec: dict, failures: list[str]) -> None:
    path_name = f"{section_type}.liquid"
    if set(schema) != {"name", "tag", "class", "max_blocks", "settings", "blocks", "presets"}:
        fail(f"{path_name}: schema top-level field inventory is not closed", failures)
    if schema.get("name") != spec["name"] or schema.get("tag") != "section" or schema.get("class") != f"section-{section_type}":
        fail(f"{path_name}: schema name/tag/class differ from contract", failures)
    if type(schema.get("max_blocks")) is not int or schema.get("max_blocks") != spec["max_blocks"]:
        fail(f"{path_name}: max_blocks must be integer {spec['max_blocks']}", failures)
    validate_setting_inventory(schema.get("settings"), spec["settings"], f"{path_name} section", failures)

    blocks = schema.get("blocks")
    if not isinstance(blocks, list) or len(blocks) != 1 or not isinstance(blocks[0], dict):
        fail(f"{path_name}: schema must declare exactly one block object", failures)
        block = {}
    else:
        block = blocks[0]
    if set(block) != {"type", "name", "limit", "settings"}:
        fail(f"{path_name}: block schema field inventory is not closed", failures)
    if block.get("type") != spec["block_type"] or block.get("name") != spec["block_name"]:
        fail(f"{path_name}: block type/name differ from contract", failures)
    if type(block.get("limit")) is not int or block.get("limit") != spec["max_blocks"]:
        fail(f"{path_name}: block limit must be integer {spec['max_blocks']}", failures)
    validate_setting_inventory(block.get("settings"), spec["block_settings"], f"{path_name} block", failures)

    presets = schema.get("presets")
    if not isinstance(presets, list) or len(presets) != 1 or not isinstance(presets[0], dict):
        fail(f"{path_name}: exactly one preset object is required", failures)
        return
    preset = presets[0]
    if set(preset) != {"name", "blocks"} or preset.get("name") != spec["name"]:
        fail(f"{path_name}: preset field inventory/name differs from contract", failures)
    preset_blocks = preset.get("blocks")
    if not isinstance(preset_blocks, list) or not spec["minimum"] <= len(preset_blocks) <= spec["max_blocks"]:
        fail(f"{path_name}: preset block count violates contract", failures)
        return
    for index, item in enumerate(preset_blocks):
        if not isinstance(item, dict) or set(item) != {"type", "settings"}:
            fail(f"{path_name}: preset block {index} field inventory is not closed", failures)
            continue
        if item.get("type") != spec["block_type"]:
            fail(f"{path_name}: preset contains an unknown block type", failures)
        settings = item.get("settings")
        if not isinstance(settings, dict) or set(settings) != spec["preset_keys"]:
            fail(f"{path_name}: preset block {index} setting keys differ from contract", failures)


def validate_section(section_type: str, spec: dict, failures: list[str]) -> None:
    liquid_path = ROOT / "sections" / f"{section_type}.liquid"
    css_path = ROOT / "assets" / spec["css"]
    if not liquid_path.is_file() or not css_path.is_file():
        fail(f"{section_type}: owned Liquid/CSS pair is missing", failures)
        return
    liquid = liquid_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    schema = schema_from(liquid, liquid_path, failures)
    validate_schema(schema, section_type, spec, failures)

    expected_include = "{{ '" + spec["css"] + "' | asset_url | stylesheet_tag }}"
    if liquid.count(expected_include) != 1:
        fail(f"{liquid_path.name}: exactly one scoped stylesheet include is required", failures)

    inventory = block_case_inventory(liquid)
    if inventory is None:
        fail(f"{liquid_path.name}: renderer needs a closed block.type case", failures)
    else:
        known, _has_nested_else, body = inventory
        if known != [spec["block_type"]]:
            fail(f"{liquid_path.name}: renderer block when inventory is not exactly {spec['block_type']!r}", failures)
        expected_attributes = 2 if section_type == "fc-about-hero" else 1
        if body.count("{{ block.shopify_attributes }}") != expected_attributes:
            fail(f"{liquid_path.name}: every rendered block branch needs its own block.shopify_attributes", failures)

    for token in FORBIDDEN_LIQUID:
        if token.lower() in liquid.lower():
            fail(f"{liquid_path.name}: forbidden page-local system token {token!r}", failures)

    root_class = f".{section_type}"
    selectors = css_selectors(css)
    if not selectors:
        fail(f"{css_path.name}: no CSS selectors found", failures)
    for selector in selectors:
        if not re.match(r"^" + re.escape(root_class) + r"(?=$|[\s.#:\[>+~_-])", selector):
            fail(f"{css_path.name}: selector can escape section scope: {selector!r}", failures)
        if re.search(r"(?<![-\w])\.button(?:--(?:primary|secondary))?(?![-\w])", selector):
            fail(f"{css_path.name}: selector overrides global button authority: {selector!r}", failures)
    if "@media (min-width: 1024px)" not in css:
        fail(f"{css_path.name}: missing reviewed desktop content breakpoint", failures)


def require_regex(text: str, pattern: str, message: str, failures: list[str], count: int = 1) -> None:
    matches = re.findall(pattern, text, re.S)
    if len(matches) != count:
        fail(message, failures)


def validate_specific_contracts(failures: list[str]) -> None:
    hero = (ROOT / "sections/fc-about-hero.liquid").read_text(encoding="utf-8")
    for style in ("primary", "secondary"):
        require_regex(
            hero,
            rf'<a\s+class="button button--{style} fc-about-hero__action"\s+href="{{{{\s*block\.settings\.link\s*\|\s*escape\s*}}}}"\s+{{{{\s*block\.shopify_attributes\s*}}}}>',
            f"fc-about-hero.liquid: {style} action must escape its independent URL and own Theme Editor attributes",
            failures,
        )
    if "block.settings.style" not in hero:
        fail("fc-about-hero.liquid: action style must remain block-owned", failures)
    merchant_media = re.search(r"if section\.settings\.image != blank(.*?)else", hero, re.S)
    fallback_media = re.search(r"{%- else -%}(.*?){%- endif -%}", hero, re.S)
    if not merchant_media or "image_url: width: 2560" not in merchant_media.group(1) or "widths: '375, 550, 750, 1100, 1500, 2000, 2560'" not in merchant_media.group(1):
        fail("fc-about-hero.liquid: merchant-selected content image needs the reviewed responsive candidates", failures)
    fallback = fallback_media.group(1) if fallback_media else ""
    for token in ("asset_img_url: '375x'", "asset_img_url: '550x'", "asset_img_url: '750x'", "asset_img_url: '1100x'", "asset_img_url: '1500x'", "asset_img_url: '2000x'", "asset_img_url: '2560x'", 'width="2731"', 'height="4096"'):
        if token not in fallback:
            fail(f"fc-about-hero.liquid: responsive fallback media is missing {token!r}", failures)
    require_regex(hero, r'class="fc-about-hero__overlay".*?alt="".*?width="2880"\s+height="1920".*?aria-hidden="true"', "fc-about-hero.liquid: decorative overlay needs exact intrinsic dimensions and semantics", failures)

    values = (ROOT / "sections/fc-about-values.liquid").read_text(encoding="utf-8")
    stable_case = re.search(r"case\s+block\.id(.*?)endcase", values, re.S)
    if not stable_case:
        fail("fc-about-values.liquid: fallback icon ownership must use stable block.id", failures)
    else:
        cases = re.findall(r"when\s+['\"]([^'\"]+)['\"]", stable_case.group(1))
        if cases != ["value_pricing", "value_quality", "value_local"]:
            fail("fc-about-values.liquid: stable migrated icon ID inventory differs from contract", failures)
        if "block.settings.heading" in stable_case.group(0):
            fail("fc-about-values.liquid: mutable heading may not select fallback media", failures)
    if "if block.settings.icon != blank" not in values or "image_tag: class: icon_class" not in values:
        fail("fc-about-values.liquid: merchant icon picker must override the owned fallback", failures)
    for asset, width, height in (("freshclub-value-freshness.png", 1224, 1276), ("freshclub-value-pricing.png", 1098, 1422), ("freshclub-value-quality.png", 1473, 1060), ("freshclub-value-local.png", 1348, 1158)):
        if asset not in values or f"assign fallback_width = {width}" not in values or f"assign fallback_height = {height}" not in values:
            fail(f"fc-about-values.liquid: exact fallback ownership/dimensions missing for {asset}", failures)
    require_regex(values, r'<section\s+class="fc-about-values"\s+aria-labelledby="AboutValuesHeading-{{ section\.id }}">\s*<h2\s+id="AboutValuesHeading-{{ section\.id }}"\s+class="fc-about-values__section-heading">', "fc-about-values.liquid: section needs a labelled h2 outline heading", failures)

    values_css = (ROOT / "assets/fc-about-values.css").read_text(encoding="utf-8")
    dimensions = {
        "freshness": (("28.52", "29.76"), ("46", "48")),
        "pricing": (("24.8", "32.24"), ("40", "52")),
        "quality": (("34.72", "24.8"), ("56", "40")),
        "local": (("31.62", "27.28"), ("51", "44")),
    }
    desktop = values_css.split("@media (min-width: 1024px)", 1)[-1]
    mobile = values_css.split("@media (min-width: 1024px)", 1)[0]
    for identity, (mobile_size, desktop_size) in dimensions.items():
        mobile_pattern = rf"\.fc-about-values__icon-image--{identity}\s*{{[^}}]*width:\s*{re.escape(mobile_size[0])}px;[^}}]*height:\s*{re.escape(mobile_size[1])}px;"
        desktop_pattern = rf"\.fc-about-values__icon-image--{identity}\s*{{[^}}]*width:\s*{re.escape(desktop_size[0])}px;[^}}]*height:\s*{re.escape(desktop_size[1])}px;"
        require_regex(mobile, mobile_pattern, f"fc-about-values.css: {identity} mobile icon size differs from authority", failures)
        require_regex(desktop, desktop_pattern, f"fc-about-values.css: {identity} desktop icon size differs from authority", failures)
    if re.search(r"\.fc-about-values__icon-image\s*{[^}]*(?:width|height)\s*:", values_css, re.S):
        fail("fc-about-values.css: generic icon dimensions may not erase per-icon sizing", failures)

    metrics = (ROOT / "sections/fc-about-metrics.liquid").read_text(encoding="utf-8")
    require_regex(metrics, r'<section\s+class="fc-about-metrics"\s+aria-labelledby="AboutMetricsHeading-{{ section\.id }}">\s*<h2\s+id="AboutMetricsHeading-{{ section\.id }}"\s+class="fc-about-metrics__section-heading">', "fc-about-metrics.liquid: section needs a labelled h2 outline heading", failures)
    if "block.settings.heading" not in metrics or "newline_to_br" in metrics:
        fail("fc-about-metrics.liquid: metric heading ownership/line-break policy differs from contract", failures)


def validate_pins(failures: list[str]) -> None:
    for relative, expected in PRODUCTION_SHA256.items():
        path = ROOT / relative
        if not path.is_file():
            fail(f"{relative}: pinned production file missing", failures)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            fail(f"{relative}: production SHA-256 mismatch ({actual})", failures)


def main() -> int:
    failures: list[str] = []
    for section_type, spec in SECTION_SPECS.items():
        validate_section(section_type, spec, failures)
    validate_specific_contracts(failures)
    validate_pins(failures)
    if failures:
        print("About sections A validation failed:", file=sys.stderr)
        for message in failures:
            print(f"- {message}", file=sys.stderr)
        return 1
    print("About sections A validation passed: closed semantics and six production SHA-256 pins verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
