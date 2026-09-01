from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def text(path: str) -> str:
    file_path = ROOT / path
    require(file_path.is_file(), f"missing {path}")
    return file_path.read_text(encoding="utf-8") if file_path.is_file() else ""


def liquid_schema(source: str, path: str) -> dict:
    match = re.search(r"{% schema %}\s*(\{.*?\})\s*{% endschema %}", source, re.S)
    require(match is not None, f"missing schema in {path}")
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        require(False, f"invalid schema in {path}: {exc}")
        return {}


def parse_json_with_shopify_header(source: str, path: str) -> dict:
    try:
        return json.loads(re.sub(r"^/\*.*?\*/\s*", "", source, flags=re.S))
    except json.JSONDecodeError as exc:
        require(False, f"invalid JSON in {path}: {exc}")
        return {}


def css_rule_blocks(source: str, selector: str) -> list[str]:
    """Return exact selector blocks after removing comment decoys."""
    uncommented = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.findall(rf"(?<![\w-]){re.escape(selector)}\s*\{{([^{{}}]*)\}}", uncommented, flags=re.S)


def css_values(source: str, selector: str, property_name: str) -> list[str]:
    values: list[str] = []
    for block in css_rule_blocks(source, selector):
        values.extend(value.strip() for value in re.findall(rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*([^;}}]+)", block))
    return values


def css_matching_brace(source: str, opening_brace: int) -> int:
    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def css_media_bodies(source: str, min_width: str) -> list[str]:
    uncommented = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    pattern = re.compile(rf"@media\s*\(\s*min-width\s*:\s*{re.escape(min_width)}\s*\)\s*\{{", re.I)
    bodies: list[str] = []
    for match in pattern.finditer(uncommented):
        opening_brace = match.end() - 1
        closing_brace = css_matching_brace(uncommented, opening_brace)
        require(closing_brace != -1, f"unclosed media query for min-width {min_width}")
        if closing_brace != -1:
            bodies.append(uncommented[opening_brace + 1 : closing_brace])
    return bodies


def css_without_media_queries(source: str) -> str:
    uncommented = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"@media\b[^{}]*\{", uncommented, flags=re.I):
        opening_brace = match.end() - 1
        closing_brace = css_matching_brace(uncommented, opening_brace)
        require(closing_brace != -1, "unclosed media query")
        if closing_brace != -1:
            spans.append((match.start(), closing_brace + 1))
    for start, end in reversed(spans):
        uncommented = uncommented[:start] + uncommented[end:]
    return uncommented


def css_top_level_rule_source(source: str, scope_name: str) -> str:
    """Keep only qualified rules that are direct children of one CSS scope."""
    uncommented = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    rules: list[str] = []
    cursor = 0
    while cursor < len(uncommented):
        opening_brace = uncommented.find("{", cursor)
        if opening_brace == -1:
            break
        prelude = uncommented[cursor:opening_brace].strip()
        closing_brace = css_matching_brace(uncommented, opening_brace)
        require(closing_brace != -1, f"unclosed rule in {scope_name}")
        if closing_brace == -1:
            break
        body = uncommented[opening_brace + 1 : closing_brace]
        if prelude.startswith("@"):
            cursor = closing_brace + 1
            continue
        require("{" not in body and "}" not in body, f"nested qualified rule is not allowed in {scope_name}")
        if "{" not in body and "}" not in body:
            rules.append(f"{prelude} {{{body}}}")
        cursor = closing_brace + 1
    return "\n".join(rules)


contract_paths = [
    "docs/homepage/shopify-section-map.md",
    "docs/homepage/editor-schema-contract.json",
    "docs/homepage/responsive-contract.json",
    "docs/homepage/interaction-contract.json",
    "docs/homepage/content-migration-contract.json",
    "docs/homepage/file-ownership.json",
]
for contract_path in contract_paths:
    text(contract_path)

hero_path = "sections/fc-home-hero.liquid"
benefits_path = "sections/fc-home-benefits.liquid"
story_path = "sections/fc-home-story.liquid"
cta_path = "sections/fc-home-cta.liquid"
hero = text(hero_path)
benefits = text(benefits_path)
story = text(story_path)
cta = text(cta_path)
hero_css = text("assets/fc-home-hero.css")
benefits_css = text("assets/fc-home-benefits.css")
story_css = text("assets/fc-home-story.css")
cta_css = text("assets/fc-home-cta.css")
template_source = text("templates/index.json")
package_source = text("package.json")

require(
    hashlib.sha256((ROOT / "assets/fc-home-hero.css").read_bytes()).hexdigest()
    == "834d95c7a569774c7a855eea7dade372ed771fa43a0d32e65aa75b7b06cfd890",
    "hero CSS byte drift: exact reviewed responsive cascade required",
)
require(
    hashlib.sha256(benefits_css.encode("utf-8")).hexdigest() == "436bf4a3cf16cba35d973ac8e175ce80c868ac650e6207268d1f20f66c2cf0ef",
    "benefits CSS byte drift: exact reviewed oval cascade required",
)
require(
    hashlib.sha256(story_css.encode("utf-8")).hexdigest() == "c0668f8f31b5deb6671ae87b5f56b48fc00bce58ac8a643d6c7be576123297f2",
    "story CSS byte drift: exact reviewed cascade required",
)

hero_schema = liquid_schema(hero, hero_path)
benefits_schema = liquid_schema(benefits, benefits_path)
story_schema = liquid_schema(story, story_path)
cta_schema = liquid_schema(cta, cta_path)

require(hero_schema.get("name") == "Home — Hero", "hero editor name")
require(hero_schema.get("max_blocks") == 2, "hero supports exactly two actions")
hero_action = next((b for b in hero_schema.get("blocks", []) if b.get("type") == "action"), {})
hero_action_settings = {s.get("id"): s.get("type") for s in hero_action.get("settings", [])}
require(hero_action_settings == {"heading": "text", "link": "url", "style": "select"}, "hero actions own label/link/style")
require("block.shopify_attributes" in hero, "hero actions expose block.shopify_attributes")
require("button button--primary" in hero and "button button--secondary" in hero, "hero reuses global buttons")
require("freshclub-home-hero-base.png" in hero and "freshclub-home-hero-overlay.png" in hero, "hero uses packaged Figma fallbacks")
require("image_tag" in hero and "fetchpriority: 'high'" in hero, "hero merchant image is responsive and eager")

require(benefits_schema.get("name") == "Home — Benefits", "benefits editor name")
require(benefits_schema.get("max_blocks") == 8, "benefits max blocks")
benefit_block = next((b for b in benefits_schema.get("blocks", []) if b.get("type") == "benefit"), {})
benefit_settings = {s.get("id"): s.get("type") for s in benefit_block.get("settings", [])}
require(benefit_settings == {"icon": "image_picker", "heading": "text", "text": "textarea", "fallback_asset": "select"}, "benefit owns icon/title/text/fallback")
require("block.shopify_attributes" in benefits, "benefit exposes block.shopify_attributes")
require('class="fc-home-benefits__oval-stack"' in benefits and 'aria-hidden="true"' in benefits, "benefits render a decorative exact Figma oval stack")
require(benefits.count("freshclub-home-ellipse-mint.svg") == 2, "benefits render the two overlapping Figma mint ellipse layers")
for index in range(1, 5):
    require(f"freshclub-home-benefit-{index:02}.png" in benefits, f"benefits support fallback {index:02}")

require(story_schema.get("name") == "Home — Story", "story editor name")
require(story_schema.get("max_blocks") == 6, "story max blocks")
story_block = next((b for b in story_schema.get("blocks", []) if b.get("type") == "story"), {})
story_settings = {s.get("id"): s.get("type") for s in story_block.get("settings", [])}
expected_story_settings = {
    "image": "image_picker", "image_alt": "text", "heading": "text", "text": "textarea",
    "button_label": "text", "button_link": "url", "button_style": "select",
    "image_side": "select", "fallback_asset": "select",
}
require(story_settings == expected_story_settings, "story owns media/copy/action/layout")
require("block.shopify_attributes" in story, "story exposes block.shopify_attributes")
require("{% if section.settings.heading != blank %} aria-labelledby=\"HomeStoryHeading-{{ section.id }}\"{% endif %}" in story, "story labels section only when its editable heading renders")
image_tag_loading_values = re.findall(r"(?m)^\s*loading:\s*([^,\n]+)", story)
fallback_image_tags = re.findall(r'<img\b(?=[^>]*class="fc-home-story__image")[^>]*>', story, flags=re.S)
html_loading_values = [match.group(1) for tag in fallback_image_tags if (match := re.search(r'\bloading\s*=\s*"([^"]+)"', tag))]
require(not re.search(r"\bassign\s+\w*loading\b", story) and "forloop." not in story, "story media loading must not depend on assigned or positional state")
require(image_tag_loading_values == ["'eager'"], "story image picker must have one unconditional eager loading value")
require(html_loading_values == ["eager"], "story fallback must have one unconditional eager loading value")
require("button button--primary" in story and "button button--secondary" in story, "story reuses global buttons")
require('class="fc-home-story__oval"' in story and 'aria-hidden="true"' in story, "each story row renders a decorative exact Figma oval band")
require(story.count("freshclub-home-ellipse-white.svg") == 1 and story.count("freshclub-home-ellipse-mint.svg") == 1, "story oval markup exposes exact white and mint Figma assets for positional alternation")
for connector_asset in ["freshclub-home-story-connector-right-to-left.svg", "freshclub-home-story-connector-left-to-right.svg"]:
    require(connector_asset in story, f"story renders exact Figma connector {connector_asset}")
require('class="fc-home-story__connector-image"' in story, "story connectors render as decorative exact SVG images")
story_media_match = re.search(r'<div class="fc-home-story__media">(.*?)</div>', story, flags=re.S)
require(story_media_match is not None and '<span class="fc-home-story__connector"' in story_media_match.group(1) and story.count('<span class="fc-home-story__connector"') == 1, "story connector must be positioned once inside its media containing block")
require('width="398"' in story and 'height="278"' in story, "right-to-left story connector keeps exact Figma dimensions")
require('width="402"' in story and 'height="312"' in story, "left-to-right story connector keeps exact Figma dimensions")
for index in range(1, 4):
    require(f"freshclub-home-story-{index:02}.png" in story, f"story supports fallback {index:02}")

require(cta_schema.get("name") == "Home — Call to action", "CTA editor name")
for setting_id in ["heading", "subheading", "text", "background_image", "button_label", "button_link", "button_style"]:
    require(any(setting.get("id") == setting_id for setting in cta_schema.get("settings", [])), f"CTA owns {setting_id}")
require("{% if section.settings.heading != blank %} aria-labelledby=\"HomeCtaHeading-{{ section.id }}\"{% endif %}" in cta, "CTA labels section only when its editable heading renders")
require("loading: 'lazy'" not in cta and 'loading="lazy"' not in cta, "CTA visible media must not use native lazy loading")
require(cta.count("loading: 'eager'") == 1 and cta.count('loading="eager"') == 3, "CTA image picker, fallback and decorations load eagerly")
require("freshclub-about-cta-bg.png" in cta and "freshclub-about-cta-decoration.png" in cta, "CTA reuses verified exact assets")
require("button button--primary" in cta and "button button--secondary" in cta, "CTA reuses global buttons")

for source, name in [(hero, "hero"), (benefits, "benefits"), (story, "story"), (cta, "CTA")]:
    require("<script" not in source.lower(), f"{name} requires no page-local JavaScript")
    require("predictive-search" not in source and "newsletter-form" not in source, f"{name} does not duplicate global behavior")

for token in ["padding: 48px 20px", "flex-direction: column", "width: min(100%, 335px)", "@media (min-width: 1024px)", "padding: 80px", "max-width: 1280px", "grid-template-columns: minmax(0, 635fr) minmax(0, 536fr)", "column-gap: clamp(32px, 7.57vw, 109px)", "max-width: 536px", "font-size: 48px", "line-height: 64px"]:
    require(token in hero_css, f"hero CSS missing {token}")

hero_base_css = css_without_media_queries(hero_css)
hero_desktop_bodies = css_media_bodies(hero_css, "1024px")
require(len(hero_desktop_bodies) == 1, "hero requires exactly one 1024px desktop media query")
hero_desktop_css = hero_desktop_bodies[0] if len(hero_desktop_bodies) == 1 else ""
hero_base_top_level_css = css_top_level_rule_source(hero_base_css, "hero base scope")
hero_desktop_top_level_css = css_top_level_rule_source(hero_desktop_css, "hero 1024px scope")

strict_hero_base_css = {
    (".fc-home-hero__content", "align-items"): ["center"],
    (".fc-home-hero__copy", "align-items"): ["center"],
    (".fc-home-hero__copy", "text-align"): ["center"],
    (".fc-home-hero__heading", "width"): ["100%"],
    (".fc-home-hero__text", "width"): ["100%"],
}
for (selector, property_name), expected in strict_hero_base_css.items():
    require(css_values(hero_base_top_level_css, selector, property_name) == expected, f"hero mobile centering drift: {selector} {property_name}")

strict_hero_desktop_css = {
    (".fc-home-hero__content", "align-items"): ["flex-start"],
    (".fc-home-hero__copy", "align-items"): ["flex-start"],
    (".fc-home-hero__copy", "text-align"): ["left"],
}
for (selector, property_name), expected in strict_hero_desktop_css.items():
    require(css_values(hero_desktop_top_level_css, selector, property_name) == expected, f"hero desktop reset scope drift: {selector} {property_name}")

for token in ["padding: 64px 20px", "grid-template-columns: repeat(2, minmax(0, 1fr))", "@media (min-width: 1024px)", "grid-template-columns: repeat(4, minmax(0, 1fr))", "background: #f5faf3"]:
    require(token in benefits_css, f"benefits CSS missing {token}")
for token in ["padding: 72px 20px", "order: -1", ".fc-home-story__block > .fc-home-story__media > .fc-home-story__decoration", "display: block", "@media (min-width: 1024px)", "max-width: 1280px", "grid-template-columns: minmax(0, 648fr) minmax(0, 600fr)", "grid-template-columns: minmax(0, 600fr) minmax(0, 648fr)", "column-gap: clamp(24px, 2.223vw, 32px)", "max-width: 648px", "max-width: 600px", "aspect-ratio: 600 / 424", "linear-gradient(229.24867441220837deg", "linear-gradient(133.48200756016044deg", "box-shadow: 8px -8px 0 #ffffff", "box-shadow: -8px -8px 0 #ffffff"]:
    require(token in story_css, f"story CSS missing {token}")

strict_story_css = {
    (".fc-home-story__blocks", "position"): ["relative"],
    (".fc-home-story__blocks", "isolation"): ["isolate"],
    (".fc-home-story__block", "isolation"): [],
    (".fc-home-story__connector", "z-index"): ["3"],
    (".fc-home-story__block", "border-radius"): [],
    (".fc-home-story__oval", "display"): ["none", "block"],
    (".fc-home-story__oval", "width"): ["var(--fc-home-oval-width)"],
    (".fc-home-story__oval", "height"): ["var(--fc-home-oval-height)"],
    (".fc-home-story", "container-type"): ["inline-size"],
    (".fc-home-story__oval", "left"): ["calc(50% - 0.5px + (100vw - 100cqw - 160px) / 2)"],
    (".fc-home-story__oval", "transform"): ["translateX(-50%)"],
    (".fc-home-story__block:nth-child(even)::before", "background"): ["#f5faf3"],
    (".fc-home-story__block:nth-child(even)::before", "width"): ["100vw"],
    (".fc-home-story__block:nth-child(even)::before", "border-radius"): [],
    (".fc-home-story__block:nth-child(odd) .fc-home-story__oval", "top"): ["var(--fc-home-story-oval-standard-top)"],
    (".fc-home-story__block:nth-child(even) .fc-home-story__oval", "top"): ["var(--fc-home-story-oval-middle-top)"],
    (".fc-home-story__block:nth-child(1) .fc-home-story__oval", "top"): [],
    (".fc-home-story__block:nth-child(2) .fc-home-story__oval", "top"): [],
    (".fc-home-story__block:nth-child(3) .fc-home-story__oval", "top"): [],
    (".fc-home-story__block:nth-child(even)", "margin-top"): ["min(268px, calc(20.9375vw - 33.5px))"],
    (".fc-home-story__block:nth-child(odd):not(:first-child)", "margin-top"): ["min(310px, calc(24.21875vw - 38.75px))"],
    (".fc-home-story__image", "width"): ["305px", "520px", "min(78.3333334%, 470px)"],
    (".fc-home-story__block--image-right .fc-home-story__decoration", "top"): ["max(-7.54716982%, -32px)"],
    (".fc-home-story__block--image-right .fc-home-story__decoration", "left"): ["min(33%, 198px)"],
    (".fc-home-story__block--image-right .fc-home-story__decoration", "width"): ["min(72.3333334%, 434px)"],
    (".fc-home-story__block--image-right .fc-home-story__decoration", "height"): ["min(96.2264151%, 408px)"],
    (".fc-home-story__block--image-right .fc-home-story__image", "left"): ["min(21.6666667%, 130px)"],
    (".fc-home-story__block--image-left .fc-home-story__decoration", "top"): ["max(-7.54716982%, -32px)"],
    (".fc-home-story__block--image-left .fc-home-story__decoration", "left"): ["max(-5.3333334%, -32px)"],
    (".fc-home-story__block--image-left .fc-home-story__decoration", "width"): ["min(72.3333334%, 434px)"],
    (".fc-home-story__block--image-left .fc-home-story__decoration", "height"): ["min(96.2264151%, 408px)"],
    (".fc-home-story__block--image-right .fc-home-story__connector", "top"): ["min(91.9811321%, 390px)"],
    (".fc-home-story__block--image-right .fc-home-story__connector", "left"): ["max(-45.3333334%, -272px)"],
    (".fc-home-story__block--image-right .fc-home-story__connector", "width"): ["min(66.3333334%, 398px)"],
    (".fc-home-story__block--image-right .fc-home-story__connector", "height"): ["min(65.5660378%, 278px)"],
    (".fc-home-story__block--image-left .fc-home-story__connector", "top"): ["min(93.8679246%, 398px)"],
    (".fc-home-story__block--image-left .fc-home-story__connector", "left"): ["min(78.8333334%, 473px)"],
    (".fc-home-story__block--image-left .fc-home-story__connector", "width"): ["min(67%, 402px)"],
    (".fc-home-story__block--image-left .fc-home-story__connector", "height"): ["min(73.5849057%, 312px)"],
    (".fc-home-story__block:last-child .fc-home-story__connector", "display"): ["none"],
}
for (selector, property_name), expected in strict_story_css.items():
    require(css_values(story_css, selector, property_name) == expected, f"story CSS exact rule drift: {selector} {property_name}")

strict_benefits_css = {
    (".fc-home-benefits", "container-type"): ["inline-size"],
    (".fc-home-benefits", "min-height"): ["calc(414px + var(--fc-home-benefits-oval-tail))"],
    (".fc-home-benefits__oval-stack", "left"): ["calc(50% - 0.5px + (100vw - 100cqw - 160px) / 2)"],
    (".fc-home-benefits__oval-stack", "width"): ["var(--fc-home-oval-width)"],
    (".fc-home-benefits__oval-stack", "height"): ["var(--fc-home-oval-height)"],
}
for (selector, property_name), expected in strict_benefits_css.items():
    require(css_values(benefits_css, selector, property_name) == expected, f"benefits CSS exact rule drift: {selector} {property_name}")

for viewport in (1024, 1100, 1280, 1330, 1439, 1440):
    container_width = min(1280.0, viewport - 160.0)
    column_gap = min(32.0, max(24.0, viewport * 0.02223))
    media_height = (container_width - column_gap) * 424.0 / 1248.0
    first_connector_gap = 268.0 * container_width / 1280.0 - media_height * (390.0 + 278.0 - 424.0) / 424.0
    second_connector_gap = 310.0 * container_width / 1280.0 - media_height * (398.0 + 312.0 - 424.0) / 424.0
    require(first_connector_gap > 0.0, f"right-to-left connector overlaps next row at {viewport}px")
    require(second_connector_gap > 0.0, f"left-to-right connector overlaps next row at {viewport}px")

for expected_px in (470.0, 434.0, 408.0, 32.0, 130.0, 198.0, 398.0, 278.0, 402.0, 312.0, 268.0, 310.0):
    rendered_px = min(expected_px, (1440.0 - 160.0) * expected_px / 1280.0)
    require(rendered_px == expected_px, f"1440 story geometry must be exact: {expected_px}px")
for token in ["padding: 32px 20px", "background: rgba(22, 73, 74, 0.93)", "@media (min-width: 1024px)", "padding: 40px 80px", "border-radius: 24px"]:
    require(token in cta_css, f"CTA CSS missing {token}")

template = parse_json_with_shopify_header(template_source, "templates/index.json")
section_types = [template.get("sections", {}).get(key, {}).get("type") for key in template.get("order", [])]
require(section_types == ["fc-home-hero", "fc-home-benefits", "fc-home-story", "fc-home-cta"], "Homepage contains four semantic sections in Figma order")
require(not any(value in template_source for value in ['"header"', '"footer"', 'predictive-search', 'newsletter-form']), "Homepage template does not duplicate global shell")
require('"validate:homepage"' in package_source and "validate_homepage.py" in package_source, "package validates Homepage")

asset_hashes = {
    "freshclub-home-hero-base.png": "a7e33c9e4f0b7e70747702c413f3b8ead89b1ad6f32f6af1b619dab806e071c2",
    "freshclub-home-hero-overlay.png": "ad4f3a26251d68c91253934da8b200855877033238c7f1bc9ec9435d701fece3",
    "freshclub-home-benefit-01.png": "cd1b22b78bc0c8e3f6dd2da75ff3320fc7bf7263a8bc71c5a283f292e045870d",
    "freshclub-home-benefit-02.png": "b24ad25fb74d8ead2d9d44c1497dbde1d412e3aeddd961b0482bf552f99ae573",
    "freshclub-home-benefit-03.png": "b8f8bc78fc9e4ad749403b1c392616eecc18e9fc85078fcbcfe2a8d7b0b48661",
    "freshclub-home-benefit-04.png": "3dd751bf91b73291bbcc5a8103c223987a361f725edfe2f3480ddf72c25cbebc",
    "freshclub-home-story-01.png": "2b6f201e669b191d2cf4d444e23f5f250555ee49c473d105cd437920441502fa",
    "freshclub-home-story-02.png": "be34127fb34245930e79d32a96c0d78a1a48b311d0fa6ba1a92a86756b36a7b0",
    "freshclub-home-story-03.png": "2d30489c42a338194223ecfc593c6aa537ee40131d791d109c885ac443760a3a",
    "freshclub-home-story-connector-right-to-left.svg": "ec6577c0f6c100b53ef037630e2fd245b19c46fd0ed1e3727f9b8b3b2184ea8d",
    "freshclub-home-story-connector-left-to-right.svg": "ba4fa12d4473bf3c5e11a324ee17b2d9e616376da6991f086cfe42d77477504e",
    "freshclub-home-ellipse-mint.svg": "3ba2337f6b2170c0db3844a9d38793dc5009530fba6f6d512b237c81c6735f62",
    "freshclub-home-ellipse-white.svg": "c353e06e024a01d3a911d46cc0ec515fe1048a8eaa74c083eae708a30e0e2402",
}
for asset_name, expected_hash in asset_hashes.items():
    asset_path = ROOT / "assets" / asset_name
    require(asset_path.is_file(), f"missing exact Figma asset assets/{asset_name}")
    if asset_path.is_file():
        require(hashlib.sha256(asset_path.read_bytes()).hexdigest() == expected_hash, f"asset hash drift: assets/{asset_name}")

if ERRORS:
    raise SystemExit("Homepage validation failed:\n- " + "\n- ".join(ERRORS))
print("Homepage native section/editor/Figma contract validation passed")
