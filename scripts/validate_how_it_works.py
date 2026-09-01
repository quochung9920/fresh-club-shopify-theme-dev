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


def schema(source: str, path: str) -> dict:
    match = re.search(r"{% schema %}\s*(\{.*?\})\s*{% endschema %}", source, re.S)
    require(match is not None, f"missing schema in {path}")
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        require(False, f"invalid schema in {path}: {exc}")
        return {}


hero = text("sections/fc-how-hero.liquid")
steps = text("sections/fc-how-steps.liquid")
faq = text("sections/fc-how-faq.liquid")
cta = text("sections/fc-how-cta.liquid")
hero_css = text("assets/fc-how-hero.css")
steps_css = text("assets/fc-how-steps.css")
faq_css = text("assets/fc-how-faq.css")
cta_css = text("assets/fc-how-cta.css")
template_source = text("templates/page.how-does-it-work.json")
package_source = text("package.json")

hero_schema = schema(hero, "sections/fc-how-hero.liquid")
steps_schema = schema(steps, "sections/fc-how-steps.liquid")
faq_schema = schema(faq, "sections/fc-how-faq.liquid")
cta_schema = schema(cta, "sections/fc-how-cta.liquid")

require(hero_schema.get("name") == "How It Works — Hero", "hero editor name")
require(hero_schema.get("max_blocks") == 2, "hero supports exactly two action blocks")
hero_block_settings = {s.get("id"): s.get("type") for b in hero_schema.get("blocks", []) if b.get("type") == "action" for s in b.get("settings", [])}
require(hero_block_settings == {"heading": "text", "link": "url", "style": "select"}, "hero action owns label/link/style")
require("block.shopify_attributes" in hero, "hero action exposes block.shopify_attributes")
require("button button--primary" in hero and "button button--secondary" in hero, "hero reuses global buttons")

require(steps_schema.get("name") == "How It Works — Steps", "steps editor name")
require(steps_schema.get("max_blocks") == 8, "steps max blocks")
step_block = next((b for b in steps_schema.get("blocks", []) if b.get("type") == "step"), {})
step_settings = {s.get("id"): s.get("type") for s in step_block.get("settings", [])}
for setting_id, setting_type in {
    "number": "text", "heading": "text", "text": "textarea", "image": "image_picker",
    "image_alt": "text", "image_side": "select", "fallback_asset": "select",
}.items():
    require(step_settings.get(setting_id) == setting_type, f"step owns {setting_id}:{setting_type}")
require("block.shopify_attributes" in steps, "step exposes block.shopify_attributes")
require("image_tag" in steps and "widths:" in steps and "sizes:" in steps, "step merchant images are responsive")
for asset in [f"freshclub-how-step-{i:02}.png" for i in range(1, 5)]:
    require(asset in steps, f"steps supports fallback {asset}")

require(faq_schema.get("name") == "How It Works — FAQ", "FAQ editor name")
faq_block = next((b for b in faq_schema.get("blocks", []) if b.get("type") == "faq"), {})
faq_settings = {s.get("id"): s.get("type") for s in faq_block.get("settings", [])}
require(faq_settings == {"heading": "text", "answer": "textarea", "open_by_default": "checkbox"}, "FAQ item owns question/answer/default state")
require("<details" in faq and "<summary" in faq and "block.shopify_attributes" in faq, "FAQ uses native editable details")
require("<script" not in faq.lower(), "FAQ requires no JavaScript")

require(cta_schema.get("name") == "How It Works — CTA", "CTA editor name")
for setting_id in ["heading", "subheading", "text", "background_image", "button_label", "button_link", "button_style"]:
    require(any(setting.get("id") == setting_id for setting in cta_schema.get("settings", [])), f"CTA owns {setting_id}")
require("freshclub-about-cta-bg.png" in cta and "freshclub-about-cta-decoration.png" in cta, "CTA reuses exact Figma assets")
require("button button--primary" in cta and "button button--secondary" in cta, "CTA reuses global button variants")

for token in ["padding: 48px 20px", "font-size: 30px", "line-height: 38px", "flex-direction: column", "width: 100%", "@media (min-width: 1024px)", "padding: 96px 80px", "font-size: 48px", "line-height: 62px"]:
    require(token in hero_css, f"hero CSS missing {token}")
for token in ["padding: 56px 20px", "gap: 48px", "width: 335px", "height: 240px", "width: 305px", "height: 220px", "left: 30px", "top: 20px", "border-radius: 16px", "order: -1", ".fc-how-step > .fc-how-step__media > .fc-how-step__decoration", "display: block", "@media (min-width: 1024px)", "max-width: 1280px", "width: 600px", "height: 424px", "width: 520px", "height: 380px", "border-radius: 24px"]:
    require(token in steps_css, f"steps CSS missing {token}")
for token in ["padding: 56px 20px", "background: #f5faf3", "max-width: 908px", "details[open]", "border-top: 1px solid #eaecf0"]:
    require(token in faq_css, f"FAQ CSS missing {token}")
for token in ["padding: 32px 20px", "border-radius: 16px", "background: rgba(22, 73, 74, 0.93)", "@media (min-width: 1024px)", "padding: 40px 80px", "border-radius: 24px", "top: 131px", "width: 165px", "height: 206px"]:
    require(token in cta_css, f"CTA CSS missing {token}")

try:
    template = json.loads(re.sub(r"^/\*.*?\*/\s*", "", template_source, flags=re.S))
except json.JSONDecodeError as exc:
    template = {}
    require(False, f"invalid page template JSON: {exc}")
section_types = [template.get("sections", {}).get(key, {}).get("type") for key in template.get("order", [])]
require(section_types == ["fc-how-hero", "fc-how-steps", "fc-how-faq", "fc-how-cta"], "template contains four semantic sections in Figma order")
require(not (ROOT / "templates/page.how-it-works.json").exists(), "obsolete alternate How It Works template must be removed")
require(not any(value in template_source for value in ['"header"', '"footer"', 'predictive-search', 'newsletter-form']), "template does not duplicate global shell")
require('"validate:how-it-works"' in package_source and "validate_how_it_works.py" in package_source, "package validates How It Works")

asset_hashes = {
    "assets/freshclub-how-step-01.png": "a7e33c9e4f0b7e70747702c413f3b8ead89b1ad6f32f6af1b619dab806e071c2",
    "assets/freshclub-how-step-02.png": "be34127fb34245930e79d32a96c0d78a1a48b311d0fa6ba1a92a86756b36a7b0",
    "assets/freshclub-how-step-03.png": "2b6f201e669b191d2cf4d444e23f5f250555ee49c473d105cd437920441502fa",
    "assets/freshclub-how-step-04.png": "2d30489c42a338194223ecfc593c6aa537ee40131d791d109c885ac443760a3a",
}
for relative, expected in asset_hashes.items():
    path = ROOT / relative
    require(path.is_file(), f"missing exact Figma asset {relative}")
    if path.is_file():
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"asset hash drift: {relative}")

if ERRORS:
    raise SystemExit("How It Works validation failed:\n- " + "\n- ".join(ERRORS))
print("How It Works native section/editor/Figma contract validation passed")
