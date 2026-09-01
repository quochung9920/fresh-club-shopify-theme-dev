#!/usr/bin/env python
"""Fail-closed integration validator for the native About Us template."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "page.about-us.json"
LAYOUT = ROOT / "layout" / "theme.liquid"
PACKAGE = ROOT / "package.json"

REQUIRED_IMAGE_SOURCE_SHA256 = {
    "sections/footer.liquid": "fea76af9005f79126c5a36ac034e9005b314bee19804fd4893b392848387af56",
}

EXPECTED_SECTIONS = {
    "about_hero": "fc-about-hero",
    "about_values": "fc-about-values",
    "about_metrics": "fc-about-metrics",
    "about_story": "fc-about-story",
    "about_process": "fc-about-process",
    "about_cta": "fc-about-cta",
}
EXPECTED_ORDER = list(EXPECTED_SECTIONS)
ALLOWED_SECTION_SETTINGS = {
    "about_hero": {"heading", "text", "image", "image_alt"},
    "about_values": set(),
    "about_metrics": {"eyebrow"},
    "about_story": {"heading", "title", "text", "image", "image_alt", "button_label", "button_link", "button_style"},
    "about_process": {"heading", "intro"},
    "about_cta": {"heading", "subheading", "text", "background_image", "button_label", "button_link", "button_style"},
}
ALLOWED_BLOCK_SETTINGS = {
    "button": {"heading", "link", "style"},
    "value_card": {"icon", "heading", "text"},
    "metric": {"value", "heading"},
    "process_step": {"badge", "heading", "text"},
}
EXPECTED_SECTION_SETTINGS_SHA256 = {
    "about_hero": "f711d3943f9dc6ae0dbee1a707caca067367d15c53a20c5f5bc7a105f5fe559d",
    "about_values": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "about_metrics": "206a6681f74a02a1e6bbc3e2d57b75f3edd56f2b82cfa764ab9e2196e0dd6613",
    "about_story": "f157039e59ea32c12d994c88261c7943dca95e9bf81c845bc7b1b9490a9d07cc",
    "about_process": "e3d120a0b54a8b4a536ff4e570fc253e43fe1be77beb010459878ac9d83c5f6a",
    "about_cta": "b6bdc0ea2236a44600a3694b9d7119a386343db8447d90a16abe5b1a1fb5183a",
}
EXPECTED_BLOCK_SETTINGS_SHA256 = {
    "about_hero.hero_primary_action": "22b75b4f2d3def18c162e47830edfc9ba35b0dc0191c67e4d1bca762ef5d789d",
    "about_hero.hero_secondary_action": "68e72a6aa50e5aa5cc04afaa3562b64441598566d035760ea8ddb3f5e03f07a1",
    # Merchant-selected image_picker values from Shopify Theme Editor commit
    # 6f529181e3021d893c393f6648d76fa735b57bdc are part of the exact payload.
    "about_values.value_freshness": "c75dff061ecdf4ae108c13ca1f66c213b5f90d99a277674ccc09765926a15121",
    "about_values.value_pricing": "590cfbc788c7d1ef85f97813290746d349bc368971b737911cc9c1c0476cf022",
    "about_values.value_quality": "6f30e336602428043c981c5a6700781a5dff3913568b3e1507299729cff65efd",
    "about_values.value_local": "1eabcfc32d77c9cdbebf8e4374e67d22cab027e984c066c5adef6f03d1c16ee5",
    "about_metrics.stat_orders": "0095fb375bf11928a909ce4fa7648746ceb6c4c825b6b15b3cbe61f35da97087",
    "about_metrics.stat_market": "23ae29c27a4fe883c33e11ae11c8e61a97fa1530c3e8ac5f30093483c45686ce",
    "about_metrics.stat_fees": "94af7eb21a979cccdb49a332bfe488106944c2f0b310342047a9b3c10cc4efd7",
    "about_metrics.stat_guarantee": "8996a7309225f3bbfc9d4864fe79fa1cfae21a3266479b2417231a645735576a",
    "about_process.step_order": "cd54cd78736f01fca1acf0df4c0e62e536774a22a5763cd95aabdad3a143a3bf",
    "about_process.step_market": "116587e2ddac57b5a0b0038c482d407613c2bb330c5f32d05921195bfc91b5e0",
    "about_process.step_pack": "77d5e94af7aecde8873504d7912e986b120924385f1974d435abf1830064f24d",
    "about_process.step_delivery": "c68a0121cf6eb53e63c6e2d9ca5f3b4e4a0efda812804844f7b8a02d3d049eee",
}
REQUIRED_FALLBACK_ASSET_SHA256 = {
    "assets/freshclub-about-hero-base.jpg": "a7e33c9e4f0b7e70747702c413f3b8ead89b1ad6f32f6af1b619dab806e071c2",
    "assets/freshclub-about-hero-overlay.jpg": "ad4f3a26251d68c91253934da8b200855877033238c7f1bc9ec9435d701fece3",
    "assets/freshclub-value-ring.png": "68c8dc81162a98c3c3b2849016079a3ff83e7e675ee3aacaf4fa87753207848d",
    "assets/freshclub-value-freshness.png": "cd1b22b78bc0c8e3f6dd2da75ff3320fc7bf7263a8bc71c5a283f292e045870d",
    "assets/freshclub-value-pricing.png": "b24ad25fb74d8ead2d9d44c1497dbde1d412e3aeddd961b0482bf552f99ae573",
    "assets/freshclub-value-quality.png": "b8f8bc78fc9e4ad749403b1c392616eecc18e9fc85078fcbcfe2a8d7b0b48661",
    "assets/freshclub-value-local.png": "3dd751bf91b73291bbcc5a8103c223987a361f725edfe2f3480ddf72c25cbebc",
    "assets/freshclub-about-story.jpg": "2b6f201e669b191d2cf4d444e23f5f250555ee49c473d105cd437920441502fa",
    "assets/freshclub-about-cta-bg.png": "cc78de89e7475bb7e8e16542432ebfb7fb0575cb9393f77b5e3708c84d9815c8",
    "assets/freshclub-about-cta-decoration.png": "85fbabde7f530953aa6f80e864f12d5ea938aa2bb52e926600c2478c6b431826",
}
REMOVED_MONOLITH_PATHS = {
    "sections/about-us-figma.liquid",
    "assets/about-us-figma.css",
    "assets/about-us-figma.js",
    "assets/gsap-3.13.0.min.js",
}
EXPECTED_BLOCKS = {
    "about_hero": [
        ("hero_primary_action", "button"),
        ("hero_secondary_action", "button"),
    ],
    "about_values": [
        ("value_freshness", "value_card"),
        ("value_pricing", "value_card"),
        ("value_quality", "value_card"),
        ("value_local", "value_card"),
    ],
    "about_metrics": [
        ("stat_orders", "metric"),
        ("stat_market", "metric"),
        ("stat_fees", "metric"),
        ("stat_guarantee", "metric"),
    ],
    "about_process": [
        ("step_order", "process_step"),
        ("step_market", "process_step"),
        ("step_pack", "process_step"),
        ("step_delivery", "process_step"),
    ],
}
LEGACY_TEMPLATE_TYPES = {"about-us-figma"}
LEGACY_PAGE_COMPONENT_TOKENS = {
    "fc-site-header",
    "fc-site-footer",
    "fc-search-field",
    "about-us-figma.js",
    "gsap-3.13.0.min.js",
}


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def load_json(path: Path) -> dict:
    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{path.relative_to(ROOT)}: duplicate JSON key {key!r}")
            result[key] = value
        return result

    raw = path.read_text(encoding="utf-8-sig")
    raw = re.sub(r"^\s*/\*.*?\*/\s*", "", raw, count=1, flags=re.DOTALL)
    return json.loads(raw, object_pairs_hook=unique_object)


def settings_digest(value: dict) -> str:
    serialized = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def load_section_schema(section_type: str) -> dict:
    relative = Path("sections") / f"{section_type}.liquid"
    source = (ROOT / relative).read_text(encoding="utf-8")
    match = re.search(r"{%\s*schema\s*%}\s*(.*?)\s*{%\s*endschema\s*%}", source, re.S)
    if match is None:
        raise ValueError(f"{relative}: schema is missing")
    return json.loads(match.group(1))


def validate_template(failures: list[str]) -> None:
    data = load_json(TEMPLATE)
    unknown_template_keys = set(data) - {"sections", "order"}
    if unknown_template_keys:
        fail(f"template has unknown top-level keys {sorted(unknown_template_keys)}", failures)
    if set(data) != {"sections", "order"}:
        fail("template must contain exactly sections and order", failures)
    sections = data.get("sections")
    if not isinstance(sections, dict):
        fail("template sections must be an object", failures)
        return
    if list(sections) != EXPECTED_ORDER:
        fail(f"template section IDs/order must be {EXPECTED_ORDER}", failures)
    if data.get("order") != EXPECTED_ORDER:
        fail(f"template order must be {EXPECTED_ORDER}", failures)

    types = [section.get("type") for section in sections.values() if isinstance(section, dict)]
    if any(section_type in LEGACY_TEMPLATE_TYPES for section_type in types):
        fail("legacy about-us-figma section must not be composed", failures)
    for section_id, expected_type in EXPECTED_SECTIONS.items():
        section = sections.get(section_id)
        if not isinstance(section, dict):
            fail(f"missing native section {section_id}", failures)
            continue
        if section.get("type") != expected_type:
            fail(f"{section_id}: expected type {expected_type}", failures)
        expected_blocks = EXPECTED_BLOCKS.get(section_id)
        allowed_section_keys = {"type", "settings"}
        if expected_blocks is not None:
            allowed_section_keys.update({"blocks", "block_order"})
        unknown_section_keys = set(section) - allowed_section_keys
        if unknown_section_keys:
            fail(f"{section_id}: unknown section keys {sorted(unknown_section_keys)}", failures)
        settings = section.get("settings")
        if not isinstance(settings, dict):
            fail(f"{section_id}: settings must be an object", failures)
        else:
            unknown_settings = set(settings) - ALLOWED_SECTION_SETTINGS[section_id]
            if unknown_settings:
                fail(f"{section_id}: unknown settings {sorted(unknown_settings)}", failures)
            expected_settings_digest = EXPECTED_SECTION_SETTINGS_SHA256[section_id]
            if settings_digest(settings) != expected_settings_digest:
                fail(f"{section_id}: migrated settings payload changed", failures)
        if expected_blocks is None:
            if section.get("blocks") not in (None, {}):
                fail(f"{section_id}: fixed section may not contain blocks", failures)
            continue
        blocks = section.get("blocks")
        expected_ids = [block_id for block_id, _ in expected_blocks]
        if not isinstance(blocks, dict) or list(blocks) != expected_ids:
            fail(f"{section_id}: block IDs/order must be {expected_ids}", failures)
            continue
        if section.get("block_order") != expected_ids:
            fail(f"{section_id}: block_order must be {expected_ids}", failures)
        for block_id, expected_type in expected_blocks:
            block = blocks.get(block_id)
            if not isinstance(block, dict) or block.get("type") != expected_type:
                fail(f"{section_id}.{block_id}: expected type {expected_type}", failures)
                continue
            unknown_block_keys = set(block) - {"type", "settings"}
            if unknown_block_keys:
                fail(f"{section_id}.{block_id}: unknown block keys {sorted(unknown_block_keys)}", failures)
            block_settings = block.get("settings")
            if not isinstance(block_settings, dict):
                fail(f"{section_id}.{block_id}: settings must be an object", failures)
                continue
            unknown_block_settings = set(block_settings) - ALLOWED_BLOCK_SETTINGS[expected_type]
            if unknown_block_settings:
                fail(f"{section_id}.{block_id}: unknown settings {sorted(unknown_block_settings)}", failures)
            expected_block_digest = EXPECTED_BLOCK_SETTINGS_SHA256[f"{section_id}.{block_id}"]
            if settings_digest(block_settings) != expected_block_digest:
                fail(f"{section_id}.{block_id}: migrated settings payload changed", failures)

    hero = sections.get("about_hero", {})
    hero_blocks = hero.get("blocks", {}) if isinstance(hero, dict) else {}
    hero_links = [
        hero_blocks.get(block_id, {}).get("settings", {}).get("link")
        for block_id in ("hero_primary_action", "hero_secondary_action")
    ]
    if hero_links != ["shopify://collections/all", "shopify://collections/all"]:
        fail("Hero actions must each own the migrated products URL", failures)

    story_settings = sections.get("about_story", {}).get("settings", {})
    if story_settings.get("button_link") != "shopify://pages/how-does-it-work":
        fail("Story action must own the migrated process URL", failures)
    cta_settings = sections.get("about_cta", {}).get("settings", {})
    if cta_settings.get("button_link") != "shopify://collections/all":
        fail("CTA action must own the migrated products URL", failures)

    process = sections.get("about_process", {})
    for block in process.get("blocks", {}).values() if isinstance(process, dict) else []:
        if "large_badge" in block.get("settings", {}):
            fail("process blocks may not retain merchant large_badge", failures)

    serialized = json.dumps(data, ensure_ascii=False)
    for token in LEGACY_PAGE_COMPONENT_TOKENS:
        if token in serialized:
            fail(f"template retains legacy page-owned component token: {token}", failures)


def validate_schema_alignment(failures: list[str]) -> None:
    for section_id, section_type in EXPECTED_SECTIONS.items():
        schema = load_section_schema(section_type)
        setting_ids = {item.get("id") for item in schema.get("settings", []) if isinstance(item, dict)}
        if setting_ids != ALLOWED_SECTION_SETTINGS[section_id]:
            fail(f"{section_type}: schema setting IDs drifted", failures)
        schema_blocks = {
            block.get("type"): {item.get("id") for item in block.get("settings", []) if isinstance(item, dict)}
            for block in schema.get("blocks", [])
            if isinstance(block, dict)
        }
        expected_blocks = EXPECTED_BLOCKS.get(section_id, [])
        expected_types = {block_type for _, block_type in expected_blocks}
        if set(schema_blocks) != expected_types:
            fail(f"{section_type}: schema block types drifted", failures)
        for block_type in expected_types:
            if schema_blocks.get(block_type) != ALLOWED_BLOCK_SETTINGS[block_type]:
                fail(f"{section_type}.{block_type}: schema setting IDs drifted", failures)


def validate_native_files(failures: list[str]) -> None:
    for section_type in EXPECTED_SECTIONS.values():
        liquid = ROOT / "sections" / f"{section_type}.liquid"
        css = ROOT / "assets" / f"{section_type}.css"
        if not liquid.is_file():
            fail(f"missing native section file: {liquid.relative_to(ROOT)}", failures)
        if not css.is_file():
            fail(f"missing native section stylesheet: {css.relative_to(ROOT)}", failures)
        if not liquid.is_file():
            continue
        source = liquid.read_text(encoding="utf-8")
        for token in LEGACY_PAGE_COMPONENT_TOKENS:
            if token in source:
                fail(f"{liquid.relative_to(ROOT)} retains legacy page-owned token: {token}", failures)
        if re.search(r"<(?:footer|nav|form|predictive-search|search-modal)\b", source, re.I):
            fail(f"{liquid.relative_to(ROOT)} emits a page-owned shell element", failures)


def validate_assets_and_removed_surface(failures: list[str]) -> None:
    for relative, expected_digest in REQUIRED_FALLBACK_ASSET_SHA256.items():
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing reviewed fallback asset: {relative}", failures)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected_digest:
            fail(f"reviewed fallback asset changed: {relative}", failures)
    for relative in REMOVED_MONOLITH_PATHS:
        if (ROOT / relative).exists():
            fail(f"obsolete About monolith surface still ships: {relative}", failures)


def validate_global_shell(failures: list[str]) -> None:
    source = LAYOUT.read_text(encoding="utf-8")
    if re.search(r"about", source, re.I):
        fail("layout must not contain any About-specific authority", failures)
    for group in ("header-group", "footer-group"):
        pattern = re.compile(r"{%-?\s*sections\s+(['\"])" + re.escape(group) + r"\1\s*-?%}", re.I)
        if len(pattern.findall(source)) != 1:
            fail(f"layout must render {group} exactly once", failures)
    if "settings.cart_type == 'drawer'" not in source or not re.search(r"{%[-]?\s*render\s+['\"]cart-drawer['\"]", source):
        fail("global cart drawer authority must remain rendered", failures)


def validate_global_button_contract(failures: list[str]) -> None:
    source = (ROOT / "assets/base.css").read_text(encoding="utf-8")
    if "/* Custom */" not in source:
        fail("base.css must retain the reviewed global button authority", failures)
        return
    custom = source.split("/* Custom */", 1)[1]
    match = re.search(r"(?m)^\.button\s*\{([^}]+)\}", custom)
    if match is None:
        fail("base.css must expose one custom global .button rule", failures)
        return
    properties = {
        item.group(1).lower(): item.group(2).strip().lower()
        for item in re.finditer(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+)", match.group(1), re.S)
    }
    expected = {
        "--buttons-radius": "8px",
        "--buttons-radius-outset": "8px",
        "--buttons-border-width": "1px",
        "min-height": "48px",
        "padding": "0 24px",
        "border-radius": "8px",
        "border": "1px solid transparent",
        "gap": "6px",
        "font-size": "16px",
        "font-weight": "500",
        "line-height": "24px",
        "white-space": "nowrap",
    }
    for name, value in expected.items():
        if properties.get(name) != value:
            fail(f"global button {name} must match HTML/Figma value {value}", failures)
    if ".button--primary:hover" not in custom or "transform: translateY(-8px)" not in custom:
        fail("global primary button must preserve the existing hover lift", failures)
    if ".button.button--secondary:not(:hover)" not in custom:
        fail("global secondary button must preserve its existing non-hover authority", failures)


class ImageTagCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[list[tuple[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "img":
            self.images.append(attrs)


def liquid_loading_arguments(source: str) -> list[str]:
    values: list[str] = []
    pattern = re.compile(
        r"(?im)^\s*loading\s*:\s*(?:'([^']*)'|\"([^\"]*)\"|([^\s,]+))\s*,?\s*$"
    )
    for match in pattern.finditer(source):
        values.append(next(value for value in match.groups() if value is not None))
    return values


def validate_required_about_image_loading(failures: list[str]) -> None:
    verified_sources: dict[str, bytes] = {}
    for relative_path, expected_sha256 in REQUIRED_IMAGE_SOURCE_SHA256.items():
        source_bytes = (ROOT / relative_path).read_bytes()
        actual_sha256 = hashlib.sha256(source_bytes).hexdigest()
        if actual_sha256 != expected_sha256:
            fail(f"{relative_path}: required-image source SHA-256 mismatch ({actual_sha256})", failures)
            return
        verified_sources[relative_path] = source_bytes

    values = (ROOT / "sections/fc-about-values.liquid").read_text(encoding="utf-8")
    story = (ROOT / "sections/fc-about-story.liquid").read_text(encoding="utf-8")
    footer = verified_sources["sections/footer.liquid"].decode("utf-8")

    if 'loading="lazy"' in values or "loading: 'lazy'" in values:
        fail("required Values images must not rely on lazy request initiation", failures)
    if values.count('loading="eager"') != 2 or values.count("loading: 'eager'") != 1:
        fail("Values ring, fallback icons, and merchant-selected icons must all be eager", failures)

    if 'loading="lazy"' in story or "loading: 'lazy'" in story:
        fail("required Story images must not rely on lazy request initiation", failures)
    if story.count('loading="eager"') != 1 or story.count("loading: 'eager'") != 1:
        fail("both Story merchant and fallback image branches must be eager", failures)

    collector = ImageTagCollector()
    collector.feed(footer)
    authority_logo_tags = []
    for attrs in collector.images:
        src_values = [value for name, value in attrs if name == "src"]
        if len(src_values) == 1 and src_values[0] is not None and "freshclub-logo-footer.png" in src_values[0]:
            authority_logo_tags.append(attrs)
    authority_loading_values = [value for name, value in authority_logo_tags[0] if name == "loading"] if len(authority_logo_tags) == 1 else []
    if authority_loading_values != ["eager"] or "settings.footer_logo" in footer:
        fail("the footer must render exactly one eager HTML-authority logo without a merchant override", failures)

    for relative_path, verified_bytes in verified_sources.items():
        current_bytes = (ROOT / relative_path).read_bytes()
        if current_bytes != verified_bytes:
            fail(f"{relative_path}: source changed during required-image validation", failures)


def validate_package_gate(failures: list[str]) -> None:
    scripts = load_json(PACKAGE).get("scripts", {})
    expected_scripts = {
        "validate:contracts": "python scripts/validate_about_us_refactor_contracts.py",
        "validate:sections-a": "python scripts/validate_about_sections_a.py",
        "validate:sections-b": "python scripts/validate_about_sections_b.py",
        "validate:about-us-native": "python scripts/validate_about_us_native_refactor.py",
        "validate:global-shell": "python scripts/validate_global_shell.py",
        "validate:how-it-works": "python scripts/validate_how_it_works.py",
        "validate:homepage": "python scripts/validate_homepage.py",
        "validate:product-detail": "python scripts/validate_product_detail.py",
        "validate:merchant-rules": "python scripts/test_merchant_product_rules.py && node scripts/test_cart_rules_guard.js",
        "test:stock-confirmation": "node scripts/test_product_form_stock_confirmation.js && python -m unittest scripts.test_stock_confirmation_contract",
        "test:product-detail:mutations": "python scripts/test_product_detail_mutations.py",
        "test:global-shell": "node scripts/test_global_shell_behavior.js",
    }
    for name, command in expected_scripts.items():
        if scripts.get(name) != command:
            fail(f"package.json must expose exact {name} gate", failures)
    expected_validate = "npm run validate:structure && npm run validate:baseline && npm run validate:theme && npm run validate:contracts && npm run validate:sections-a && npm run validate:sections-b && npm run validate:about-us-native && npm run validate:global-shell && npm run validate:how-it-works && npm run validate:homepage && npm run validate:product-detail && npm run validate:merchant-rules && npm run test:stock-confirmation && npm run test:product-detail:mutations && npm run test:global-shell"
    if scripts.get("validate") != expected_validate:
        fail("full validate command must use the exact ordered native release gates", failures)
    if "validate:about-us" in scripts:
        fail("obsolete monolith validation gate must be removed", failures)


def main() -> int:
    failures: list[str] = []
    try:
        validate_template(failures)
        validate_schema_alignment(failures)
        validate_native_files(failures)
        validate_assets_and_removed_surface(failures)
        validate_global_shell(failures)
        validate_global_button_contract(failures)
        validate_required_about_image_loading(failures)
        validate_package_gate(failures)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError) as exc:
        failures.append(str(exc))
    if failures:
        print("Native About Us integration validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Native About Us integration validation passed: six sections and one global shell.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
