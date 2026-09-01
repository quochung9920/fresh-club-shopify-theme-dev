#!/usr/bin/env python
"""Fail-closed contract validator for the lane-B About sections."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ABSENT = object()


def spec(setting_id: str, setting_type: str, default: object = ABSENT, options: list[dict] | None = None) -> dict:
    result = {"id": setting_id, "type": setting_type, "default": default}
    if options is not None:
        result["options"] = options
    return result


BUTTON_OPTIONS = [
    {"value": "primary", "label": "Primary"},
    {"value": "secondary", "label": "Secondary"},
]

CONTRACTS = {
    "story": {
        "liquid": "sections/fc-about-story.liquid",
        "css": "assets/fc-about-story.css",
        "name": "About — Story",
        "settings": [
            spec("heading", "inline_richtext", "Built by people who know what 4am market runs really cost"),
            spec("title", "text", "It started with one question"),
            spec("text", "textarea", "Why should buying fresh produce be this hard? Our founders spent years inside Sydney’s food scene — running kitchens, managing venues, and buying produce the hard way. We watched good businesses overpay and under-sleep, so we built the service we always wished existed."),
            spec("image", "image_picker"),
            spec("image_alt", "text", "The FreshClub crew at the produce markets"),
            spec("button_label", "text", "See How It Works"),
            spec("button_link", "url"),
            spec("button_style", "select", "secondary", BUTTON_OPTIONS),
        ],
        "blocks": [],
        "root": "fc-about-story",
        "heading_colors": {".fc-about-story__heading": "#16494a", ".fc-about-story__title": "#1d2939"},
    },
    "process": {
        "liquid": "sections/fc-about-process.liquid",
        "css": "assets/fc-about-process.css",
        "name": "About — Daily process",
        "settings": [
            spec("heading", "text", "A day at FreshClub"),
            spec("intro", "text", "What happens between the market floor and your kitchen door."),
        ],
        "blocks": [
            {
                "type": "process_step",
                "name": "Process step",
                "limit": 4,
                "settings": [
                    spec("badge", "text", "4AM"),
                    spec("heading", "text", "The market run"),
                    spec("text", "textarea", "We’re on the floor at Sydney’s produce markets, hand-picking your stock."),
                ],
            }
        ],
        "root": "fc-about-process",
        "heading_colors": {".fc-about-process__heading": "#16494a", ".fc-about-process__step-heading": "#16494a"},
    },
    "cta": {
        "liquid": "sections/fc-about-cta.liquid",
        "css": "assets/fc-about-cta.css",
        "name": "About — Call to action",
        "settings": [
            spec("heading", "text", "Join The Club. Buy Fresher, For Less."),
            spec("subheading", "text", "Local team. Honest prices. Market-fresh every day."),
            spec("text", "textarea", "Whether you run a restaurant, cafe, catering company, juice bar, grocer, or office — FreshClub delivers the same wholesale access, quality assurance, and simplicity trusted by Sydney’s leading businesses."),
            spec("background_image", "image_picker"),
            spec("button_label", "text", "Start Ordering Fresh"),
            spec("button_link", "url"),
            spec("button_style", "select", "primary", BUTTON_OPTIONS),
        ],
        "blocks": [],
        "root": "fc-about-cta",
        "heading_colors": {".fc-about-cta__heading": "#ffffff"},
    },
}

PROCESS_PRESET = [
    {"type": "process_step", "settings": {"badge": "TONIGHT", "heading": "You place your order", "text": "Browse live stock photos and honest prices, then lock in tomorrow’s delivery slot."}},
    {"type": "process_step", "settings": {"badge": "4AM", "heading": "The market run", "text": "We’re on the floor at Sydney’s produce markets, hand-picking your stock."}},
    {"type": "process_step", "settings": {"badge": "6AM", "heading": "Checked & packed", "text": "Our own crew quality-checks and packs every single box — no shortcuts."}},
    {"type": "process_step", "settings": {"badge": "YOUR SLOT", "heading": "Delivered fresh", "text": "Your order arrives in your chosen window, picked just hours earlier."}},
]

PRODUCTION_SHA256 = {
    "sections/fc-about-story.liquid": "017645d57b8c5658fcfc5656616fbb4951c4d4f1117e1a016e065cf046d93ea5",
    "sections/fc-about-process.liquid": "cba68781ff5339d5078e74652c7a880bb3d52dfe589a25b53006fd07518b5393",
    "sections/fc-about-cta.liquid": "b455c58e8395a91261ba569f9eed20bb1c0eaf11ba183fcd5938c20f26712b2d",
    "assets/fc-about-story.css": "57739b1a3ff05d5ae713e980116bcbfe9f032645cdd54c6f95396fe391bc0a57",
    "assets/fc-about-process.css": "96552c38fd8ecc1a8c29c9cef43c85da80a493b654ad41d20e044fad0a5b8487",
    "assets/fc-about-cta.css": "0c3aa4e22296251b9dab5710be7965fe69bed887b76d8c3b03ceb71fb9e40682",
}

SCHEMA_ROOT_KEYS = {"name", "tag", "class", "settings", "blocks", "presets"}
SETTING_KEYS = {"type", "id", "label", "default", "options"}
OPTION_KEYS = {"value", "label"}
BLOCK_KEYS = {"type", "name", "limit", "settings"}
PRESET_KEYS = {"name", "blocks"}
PRESET_BLOCK_KEYS = {"type", "settings"}
GEOMETRY_VIEWPORTS = (375, 390, 768, 1440)
DECORATIVE_SELECTOR_PREFIXES = {
    "fc-about-story": (
        ".fc-about-story__wave",
        ".fc-about-story__panel",
    ),
    "fc-about-process": (),
    "fc-about-cta": (
        ".fc-about-cta__background",
        ".fc-about-cta__background-image",
        ".fc-about-cta__decoration",
        ".fc-about-cta__decoration--left",
        ".fc-about-cta__decoration--right",
    ),
}


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def require_allowed_keys(actual: dict, allowed: set[str], relative: str, kind: str) -> None:
    unknown = set(actual) - allowed
    require(not unknown, f"{relative}: {kind} has unknown keys {sorted(unknown)!r}")


def extract_schema(source: str, path: str) -> dict:
    match = re.search(r"{%\s*schema\s*%}(.*?){%\s*endschema\s*%}", source, re.S)
    require(match is not None, f"{path}: missing schema block")
    try:
        schema = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid schema JSON: {exc}") from exc
    require(isinstance(schema, dict), f"{path}: schema must be an object")
    return schema


def validate_setting(actual: dict, expected: dict, relative: str) -> None:
    require(isinstance(actual, dict), f"{relative}: setting must be an object")
    require_allowed_keys(actual, SETTING_KEYS, relative, "setting object")
    setting_id = expected["id"]
    require(actual.get("id") == setting_id, f"{relative}: expected setting {setting_id!r}")
    require(actual.get("type") == expected["type"], f"{relative}: {setting_id} type drifted")
    if expected["default"] is ABSENT:
        require("default" not in actual, f"{relative}: {setting_id} must not define a default")
    else:
        require(actual.get("default", ABSENT) == expected["default"], f"{relative}: {setting_id} default drifted")
    if "options" in expected:
        require(actual.get("options") == expected["options"], f"{relative}: {setting_id} options drifted")
        for option in actual["options"]:
            require(isinstance(option, dict), f"{relative}: {setting_id} option must be an object")
            require_allowed_keys(option, OPTION_KEYS, relative, "option object")
    else:
        require("options" not in actual, f"{relative}: {setting_id} must not define options")


def validate_setting_list(actual: object, expected: list[dict], relative: str) -> None:
    require(isinstance(actual, list), f"{relative}: settings must be an array")
    require(len(actual) == len(expected), f"{relative}: setting collection drifted")
    for actual_setting, expected_setting in zip(actual, expected):
        validate_setting(actual_setting, expected_setting, relative)


def validate_schema(source: str, relative: str, contract: dict) -> dict:
    schema = extract_schema(source, relative)
    require_allowed_keys(schema, SCHEMA_ROOT_KEYS, relative, "schema root")
    require(schema.get("name") == contract["name"], f"{relative}: wrong section name")
    require(schema.get("tag") == "section", f"{relative}: schema tag must be section")
    validate_setting_list(schema.get("settings"), contract["settings"], relative)
    presets = schema.get("presets")
    require(isinstance(presets, list) and len(presets) == 1, f"{relative}: exactly one preset is required")
    require(isinstance(presets[0], dict), f"{relative}: preset must be an object")
    require_allowed_keys(presets[0], PRESET_KEYS, relative, "preset object")
    require(presets[0].get("name") == contract["name"], f"{relative}: preset name drifted")

    actual_blocks = schema.get("blocks", [])
    require(isinstance(actual_blocks, list) and len(actual_blocks) == len(contract["blocks"]), f"{relative}: block collection drifted")
    for actual, expected in zip(actual_blocks, contract["blocks"]):
        require(isinstance(actual, dict), f"{relative}: block must be an object")
        require_allowed_keys(actual, BLOCK_KEYS, relative, "block object")
        require(actual.get("type") == expected["type"], f"{relative}: wrong block type")
        require(actual.get("name") == expected["name"], f"{relative}: wrong block name")
        require(actual.get("limit") == expected["limit"], f"{relative}: wrong block limit")
        validate_setting_list(actual.get("settings"), expected["settings"], relative)

    preset_blocks = presets[0].get("blocks", [])
    require(isinstance(preset_blocks, list), f"{relative}: preset blocks must be an array")
    block_contracts = {item["type"]: item for item in contract["blocks"]}
    for preset_block in preset_blocks:
        require(isinstance(preset_block, dict), f"{relative}: preset block must be an object")
        require_allowed_keys(preset_block, PRESET_BLOCK_KEYS, relative, "preset block object")
        block_type = preset_block.get("type")
        require(block_type in block_contracts, f"{relative}: preset block type is not allowed")
        preset_settings = preset_block.get("settings")
        require(isinstance(preset_settings, dict), f"{relative}: preset settings must be an object")
        allowed_setting_ids = {item["id"] for item in block_contracts[block_type]["settings"]}
        require_allowed_keys(preset_settings, allowed_setting_ids, relative, "preset settings object")

    serialized = json.dumps(schema, ensure_ascii=False)
    for forbidden in ("Figma", "large_badge", "header", "footer", "newsletter", "products_url", "process_url"):
        require(forbidden not in serialized, f"{relative}: forbidden schema term {forbidden!r}")
    return schema


def matching_brace(source: str, opening: int, relative: str) -> int:
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValidationError(f"{relative}: unbalanced CSS braces")


def parse_css_rules(source: str, relative: str, contexts: tuple[str, ...] = ()) -> list[tuple[str, str, tuple[str, ...]]]:
    rules: list[tuple[str, str, tuple[str, ...]]] = []
    cursor = 0
    while cursor < len(source):
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        if cursor == len(source):
            break
        opening = source.find("{", cursor)
        require(opening >= 0, f"{relative}: stray CSS text without a rule")
        header = source[cursor:opening].strip()
        require(bool(header), f"{relative}: empty CSS rule header")
        closing = matching_brace(source, opening, relative)
        body = source[opening + 1:closing]
        if header.startswith("@"):
            require(header.lower().startswith(("@media", "@supports")), f"{relative}: unsupported at-rule {header!r}")
            rules.extend(parse_css_rules(body, relative, contexts + (header,)))
        else:
            require("{" not in body and "}" not in body, f"{relative}: malformed nested style rule")
            rules.append((header, body, contexts))
        cursor = closing + 1
    return rules


def declarations(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+)", body, re.S):
        result[match.group(1).lower()] = match.group(2).strip().lower()
    return result


def selector_is_scoped(selector: str, root: str) -> bool:
    selector = selector.strip()
    prefix = f".{root}"
    return selector == prefix or (
        selector.startswith(prefix)
        and len(selector) > len(prefix)
        and selector[len(prefix)] in "_-. :>[+~"
    )


def rules_for(rules: list[tuple[str, str, tuple[str, ...]]], selector: str, desktop: bool | None = None) -> list[dict[str, str]]:
    matches = []
    for selectors, body, contexts in rules:
        individual = [item.strip() for item in selectors.split(",")]
        is_desktop = any(re.search(r"min-width\s*:\s*1024px", context, re.I) for context in contexts)
        if selector in individual and (desktop is None or desktop == is_desktop):
            matches.append(declarations(body))
    return matches


def selector_has_sibling_combinator(selector: str) -> bool:
    bracket_depth = 0
    parenthesis_depth = 0
    quote = ""
    escaped = False
    for character in selector:
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = ""
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif character == "(":
            parenthesis_depth += 1
        elif character == ")":
            parenthesis_depth = max(0, parenthesis_depth - 1)
        elif character in "+~" and bracket_depth == 0 and parenthesis_depth == 0:
            return True
    return False


def selector_is_decorative(selector: str, root: str) -> bool:
    selector = selector.strip().lower()
    for prefix in DECORATIVE_SELECTOR_PREFIXES[root]:
        if selector == prefix:
            return True
        if not selector.startswith(prefix):
            continue
        continuation = selector[len(prefix):]
        if selector_has_sibling_combinator(continuation):
            continue
        if continuation.startswith((":", "[", ".", ">")):
            return True
        if continuation[:1].isspace() and not continuation.lstrip().startswith(("+", "~")):
            return True
    return False


def rule_has_required_content(selectors: str, root: str) -> bool:
    return any(not selector_is_decorative(item, root) for item in selectors.split(","))


def alpha_token_is_zero(token: str) -> bool:
    token = token.strip().lower()
    if token.endswith("%"):
        token = token[:-1].strip()
    try:
        return float(token) == 0
    except ValueError:
        return False


def color_is_alpha_zero(value: str) -> bool:
    value = value.strip().lower()
    if value == "transparent":
        return True
    if re.fullmatch(r"#[0-9a-f]{4}", value):
        return value[-1] == "0"
    if re.fullmatch(r"#[0-9a-f]{8}", value):
        return value[-2:] == "00"
    match = re.fullmatch(r"(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\((.*)\)", value, re.S)
    if match is None:
        return False
    arguments = match.group(1)
    if "/" in arguments:
        return alpha_token_is_zero(arguments.rsplit("/", 1)[1])
    if value.startswith(("rgba(", "hsla(")) and "," in arguments:
        return alpha_token_is_zero(arguments.rsplit(",", 1)[1])
    return False


def split_top_level(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == delimiter and depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def split_top_level_whitespace(value: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start: int | None = None
    for index, character in enumerate(value):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character.isspace() and depth == 0:
            if start is not None:
                parts.append(value[start:index])
                start = None
        elif start is None:
            start = index
    if start is not None:
        parts.append(value[start:])
    return parts


def evaluate_css_length(value: str, viewport: int, relative: str) -> float:
    value = value.strip().lower()
    function = re.fullmatch(r"(calc|min|max|clamp)\((.*)\)", value, re.S)
    if function:
        name, arguments = function.groups()
        if name == "calc":
            depth = 0
            operators: list[tuple[int, str]] = []
            for index, character in enumerate(arguments):
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                elif character in "+-" and depth == 0 and index > 0:
                    operators.append((index, character))
            if not operators:
                return evaluate_css_length(arguments, viewport, relative)
            total = evaluate_css_length(arguments[:operators[0][0]], viewport, relative)
            for operation_index, (position, operator) in enumerate(operators):
                end = operators[operation_index + 1][0] if operation_index + 1 < len(operators) else len(arguments)
                operand = evaluate_css_length(arguments[position + 1:end], viewport, relative)
                total = total + operand if operator == "+" else total - operand
            return total
        values = [evaluate_css_length(item, viewport, relative) for item in split_top_level(arguments, ",")]
        if name == "min":
            require(len(values) >= 1, f"{relative}: empty min() expression")
            return min(values)
        if name == "max":
            require(len(values) >= 1, f"{relative}: empty max() expression")
            return max(values)
        require(len(values) == 3, f"{relative}: clamp() must have three arguments")
        return max(values[0], min(values[1], values[2]))
    literal = re.fullmatch(r"([+-]?[0-9]+(?:\.[0-9]+)?)(px|em|rem|vw|vh|%)?", value)
    require(literal is not None, f"{relative}: unsupported fail-closed CSS length {value!r}")
    amount = float(literal.group(1))
    unit = literal.group(2) or "px"
    if unit in {"vw", "vh", "%"}:
        return viewport * amount / 100
    if unit in {"em", "rem"}:
        return amount * 16
    return amount


def validate_required_dimension(relative: str, property_name: str, value: str) -> None:
    for viewport in GEOMETRY_VIEWPORTS:
        measured = evaluate_css_length(value, viewport, relative)
        require(measured > 0.000001, f"{relative}: required content must have positive {property_name}")


def validate_required_font_size(relative: str, value: str) -> None:
    scalar = re.fullmatch(r"[0-9]+(?:\.[0-9]+)?px", value.strip().lower())
    require(scalar is not None, f"{relative}: required-content font-size must be a plain positive px scalar")
    require(float(value[:-2]) > 0, f"{relative}: required-content font-size must be positive")


def parse_transform_functions(value: str, relative: str) -> list[tuple[str, str]]:
    value = value.strip().lower()
    if value == "none":
        return []
    functions: list[tuple[str, str]] = []
    cursor = 0
    while cursor < len(value):
        while cursor < len(value) and value[cursor].isspace():
            cursor += 1
        if cursor == len(value):
            break
        match = re.match(r"([a-z][a-z0-9-]*)\(", value[cursor:])
        require(match is not None, f"{relative}: unsupported fail-closed transform syntax {value!r}")
        name = match.group(1)
        opening = cursor + match.end() - 1
        depth = 1
        closing = opening + 1
        while closing < len(value) and depth:
            if value[closing] == "(":
                depth += 1
            elif value[closing] == ")":
                depth -= 1
            closing += 1
        require(depth == 0, f"{relative}: unbalanced transform {value!r}")
        functions.append((name, value[opening + 1:closing - 1]))
        cursor = closing
    return functions


def validate_required_transform(relative: str, value: str) -> None:
    for name, arguments in parse_transform_functions(value, relative):
        require(name in {"scale", "scalex", "scaley", "translate", "translatex", "translatey"}, f"{relative}: unsupported fail-closed transform function {name!r}")
        if name.startswith("scale"):
            components = split_top_level(arguments, ",") if "," in arguments else split_top_level_whitespace(arguments)
            expected = 2 if name == "scale" and len(components) == 2 else 1
            require(len(components) == expected, f"{relative}: malformed {name}() transform")
            for component in components:
                require(re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", component.strip()) is not None, f"{relative}: unsupported fail-closed {name}() value")
                require(abs(float(component)) > 0.000001, f"{relative}: required content may not be scaled to zero")
            continue
        components = split_top_level(arguments, ",") if "," in arguments else split_top_level_whitespace(arguments)
        require(1 <= len(components) <= (2 if name == "translate" else 1), f"{relative}: malformed {name}() transform")
        for component in components:
            for viewport in GEOMETRY_VIEWPORTS:
                measured = abs(evaluate_css_length(component, viewport, relative))
                require(measured < viewport, f"{relative}: {name} hides required content off-canvas at {viewport}px")


def media_is_active(contexts: tuple[str, ...], viewport: int) -> bool:
    for context in contexts:
        for minimum in re.findall(r"min-width\s*:\s*([0-9]+)px", context, re.I):
            if viewport < int(minimum):
                return False
        for maximum in re.findall(r"max-width\s*:\s*([0-9]+)px", context, re.I):
            if viewport > int(maximum):
                return False
    return True


def validate_required_visibility(relative: str, props: dict[str, str]) -> None:
    require(props.get("display") != "none", f"{relative}: required content may not use display:none")
    require(props.get("content-visibility") != "hidden", f"{relative}: required content may not use content-visibility:hidden")
    require(props.get("visibility") not in {"hidden", "collapse"}, f"{relative}: required content may not use hidden visibility")
    if "opacity" in props:
        try:
            require(float(props["opacity"]) > 0, f"{relative}: zero-opacity content is forbidden")
        except ValueError as exc:
            raise ValidationError(f"{relative}: opacity must be a positive numeric value") from exc
    if "color" in props:
        require(not color_is_alpha_zero(props["color"]), f"{relative}: alpha-zero text color is forbidden")
    for property_name in ("width", "height", "max-width", "max-height"):
        if property_name in props:
            validate_required_dimension(relative, property_name, props[property_name])
    if "font-size" in props:
        validate_required_font_size(relative, props["font-size"])
    require("clip" not in props, f"{relative}: required content may not author clip")
    require("clip-path" not in props, f"{relative}: required content may not author clip-path")
    if "position" in props:
        require(props["position"] in {"static", "relative", "absolute", "fixed", "sticky"}, f"{relative}: unsupported fail-closed position value")
    if "transform" in props:
        validate_required_transform(relative, props["transform"])


def validate_geometry(relative: str, rules: list[tuple[str, str, tuple[str, ...]]], contract: dict) -> None:
    for viewport in GEOMETRY_VIEWPORTS:
        for selectors, body, contexts in rules:
            if not media_is_active(contexts, viewport) or not rule_has_required_content(selectors, contract["root"]):
                continue
            props = declarations(body)
            for property_name in ("width", "min-width", "max-width"):
                value = props.get(property_name)
                if value is None:
                    continue
                measured = evaluate_css_length(value, viewport, relative)
                should_bound = property_name != "max-width" or bool(re.search(r"(?:vw|calc\(|min\(|max\(|clamp\()", value))
                if should_bound:
                    require(measured <= viewport + 0.001, f"{relative}: {property_name} exceeds {viewport}px viewport")
            for property_name in ("left", "right", "top", "bottom"):
                value = props.get(property_name)
                if value:
                    measured = abs(evaluate_css_length(value, viewport, relative))
                    if props.get("position") in {"relative", "absolute", "fixed", "sticky"}:
                        require(measured < viewport, f"{relative}: {property_name} hides required content off-canvas at {viewport}px")
            text_indent = props.get("text-indent")
            if text_indent and text_indent.startswith("-"):
                measured = abs(evaluate_css_length(text_indent, viewport, relative))
                require(measured < viewport, f"{relative}: text-indent hides required content off-canvas at {viewport}px")



def validate_css(relative: str, css: str, contract: dict) -> list[tuple[str, str, tuple[str, ...]]]:
    require("/*" not in css and "*/" not in css, f"{relative}: CSS comments are forbidden")
    rules = parse_css_rules(css, relative)
    require(rules, f"{relative}: no CSS rules found")
    for selectors, body, _contexts in rules:
        for selector in selectors.split(","):
            require(selector_is_scoped(selector, contract["root"]), f"{relative}: unscoped or ancestor selector {selector.strip()!r}")
        if rule_has_required_content(selectors, contract["root"]):
            validate_required_visibility(relative, declarations(body))

    validate_geometry(relative, rules, contract)
    require("!important" not in css, f"{relative}: !important is forbidden")
    require(re.search(r"overflow-x\s*:\s*hidden", css, re.I) is None, f"{relative}: overflow may not be concealed")
    for selector, expected_color in contract["heading_colors"].items():
        base_rules = rules_for(rules, selector, desktop=False)
        require(len(base_rules) == 1, f"{relative}: {selector} needs one mobile-first rule")
        require(base_rules[0].get("color") == expected_color, f"{relative}: {selector} effective color drifted")
    return rules


def validate_button_allowlist(liquid: str, relative: str, safe_default: str) -> None:
    require("button--{{" not in liquid, f"{relative}: raw button style interpolation is forbidden")
    require("case section.settings.button_style" in liquid, f"{relative}: button style needs a closed case")
    require("when 'primary'" in liquid and "when 'secondary'" in liquid, f"{relative}: exact button variants are required")
    require("assign button_class = 'button button--primary'" in liquid, f"{relative}: primary static class is missing")
    require("assign button_class = 'button button--secondary'" in liquid, f"{relative}: secondary static class is missing")
    require(f"else -%}}\n{' ' * (14 if 'story' in relative else 10)}{{%- assign button_class = 'button button--{safe_default}'" in liquid, f"{relative}: safe static fallback drifted")
    require('class="{{ button_class }}"' in liquid, f"{relative}: allowlisted class is not rendered")


def validate_common(key: str, contract: dict) -> tuple[str, str, dict, list[tuple[str, str, tuple[str, ...]]]]:
    liquid_path = ROOT / contract["liquid"]
    css_path = ROOT / contract["css"]
    require(liquid_path.is_file(), f"{contract['liquid']}: required section file is absent")
    require(css_path.is_file(), f"{contract['css']}: required stylesheet is absent")
    liquid = liquid_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    schema = validate_schema(liquid, contract["liquid"], contract)
    rules = validate_css(contract["css"], css, contract)

    asset_name = Path(contract["css"]).name
    require(f"{{{{ '{asset_name}' | asset_url | stylesheet_tag }}}}" in liquid, f"{contract['liquid']}: stylesheet is not loaded")
    require(f'class="{contract["root"]}"' in liquid, f"{contract['liquid']}: missing scoped root")
    require("section.id" in liquid, f"{contract['liquid']}: root is not section-instance identifiable")
    require(".fc-btn" not in liquid + css, f"{contract['liquid']}: page-local button system is forbidden")
    require("<script" not in liquid, f"{contract['liquid']}: JavaScript is not required for these sections")
    return liquid, css, schema, rules


def validate_story(contract: dict) -> None:
    liquid, css, _schema, rules = validate_common("story", contract)
    require(re.search(r"section\.settings\.image\s*\|\s*image_url", liquid) is not None, "story: selected image needs Shopify image_url")
    widths_match = re.search(r"widths:\s*'([^']+)'", liquid)
    require(widths_match is not None and len([item for item in widths_match.group(1).split(",") if item.strip()]) >= 4, "story: selected image needs at least four responsive width candidates")
    require("sizes:" in liquid, "story: selected image needs sizes")
    require("freshclub-about-story.jpg" in liquid, "story: reviewed fallback asset is missing")
    fallback_candidates = set(re.findall(r"freshclub-about-story\.jpg'\s*\|\s*asset_img_url:\s*'([0-9]+x)'", liquid))
    require(len(fallback_candidates) >= 4, "story: fallback image needs at least four responsive candidates")
    require('srcset="' in liquid and 'sizes="(min-width: 1024px) 470px, calc(100vw - 40px)"' in liquid, "story: fallback srcset/sizes are missing")
    require('width="626"' in liquid and 'height="939"' in liquid, "story: fallback image dimensions are missing")
    require("section.settings.image_alt | escape" in liquid, "story: reviewed alt behavior is missing")
    require("order: 1" in css and "order: 2" in css, "story: mobile image-before-copy order is missing")
    require("@media (min-width: 1024px)" in css, "story: desktop composition breakpoint is missing")
    mobile_media = rules_for(rules, ".fc-about-story__media", desktop=False)
    require(len(mobile_media) == 1, "story: media needs one mobile-first rule")
    require(mobile_media[0].get("border-radius") == "16px", "story: image frame must use the 16px Figma radius")
    require(mobile_media[0].get("overflow") == "hidden", "story: rounded image frame must clip its media")
    image_rules = rules_for(rules, ".fc-about-story__image", desktop=False)
    require(len(image_rules) == 1 and image_rules[0].get("border-radius") == "inherit", "story: image must inherit the frame radius")
    panel = rules_for(rules, ".fc-about-story__body > .fc-about-story__panel", desktop=True)
    require(len(panel) == 1, "story: desktop teal image decoration needs a selector stronger than the theme div:empty rule")
    require(panel[0].get("display") == "block", "story: desktop teal image decoration must render")
    require(panel[0].get("border-radius") == "16px", "story: teal image decoration must use the 16px Figma radius")
    require(panel[0].get("width") == "434px" and panel[0].get("height") == "408px", "story: teal image decoration geometry drifted")
    require(panel[0].get("top") == "-32px" and panel[0].get("right") == "-32px", "story: teal image decoration offset drifted")
    require("linear-gradient(229.25deg, #34aeb0 12.7%, #ffffff 78.01%)" == panel[0].get("background"), "story: teal image decoration gradient drifted")
    validate_button_allowlist(liquid, contract["liquid"], "secondary")
    require("button_label != blank and section.settings.button_link != blank" in liquid, "story: blank owned link must suppress the process action")
    require("routes.all_products_collection_url" not in liquid, "story: process action may not fall back to Products")
    require("section.settings.button_link | escape" in liquid, "story: action URL must be contextually escaped")


def validate_process(contract: dict) -> None:
    liquid, css, schema, _rules = validate_common("process", contract)
    case_match = re.search(r"{%-?\s*case block\.type\s*-?%}(.*?){%-?\s*endcase\s*-?%}", liquid, re.S)
    require(case_match is not None, "process: block rendering must use a closed case")
    case_body = case_match.group(1)
    require(len(re.findall(r"{%-?\s*when\s+'process_step'\s*-?%}", case_body)) == 1, "process: exact process_step branch is required")
    require(re.search(r"{%-?\s*else\b", case_body) is None, "process: unknown blocks may not render an else branch")
    require(liquid.count('class="fc-about-process__step"') == 1 and 'class="fc-about-process__step"' in case_body, "process: step rendering must remain inside the allowlisted branch")
    require('<ol class="fc-about-process__steps">' in liquid and '<li class="fc-about-process__step" {{ block.shopify_attributes }}>' in liquid, "process: steps need ol/li semantics and editor attributes")
    require("<article" not in liquid, "process: generic article semantics are forbidden")
    require("large_badge" not in liquid + css, "process: merchant large_badge toggle is forbidden")
    require("badge_is_time" in liquid, "process: badge typography must derive from content")
    require(schema["presets"][0].get("blocks") == PROCESS_PRESET, "process: exact preset copy and order drifted")
    require("grid-template-columns: repeat(4" in css, "process: desktop four-step layout is missing")
    require("@media (min-width: 1024px)" in css, "process: narrow topology must persist through 768px")


def validate_cta(contract: dict) -> None:
    liquid, _css, _schema, rules = validate_common("cta", contract)
    require("freshclub-about-cta-bg.png" in liquid, "cta: reviewed background fallback is missing")
    require("freshclub-about-cta-decoration.png" in liquid, "cta: reviewed side decoration is missing")
    require(liquid.count('alt=""') >= 3, "cta: decorative media must have blank alt")
    require(liquid.count('aria-hidden="true"') >= 3, "cta: all decorative wrappers must be hidden from assistive technology")
    require("loading: 'lazy'" not in liquid and 'loading="lazy"' not in liquid, "cta: visible fallback media must not be lazy-loaded")
    require(liquid.count("loading: 'eager'") == 1, "cta: merchant-selected background must be eager exactly once")
    require(liquid.count('loading="eager"') == 3, "cta: fallback background and two desktop decorations must be eager")
    validate_button_allowlist(liquid, contract["liquid"], "primary")
    require("button_url | escape" in liquid, "cta: action URL must be contextually escaped")
    mobile = rules_for(rules, ".fc-about-cta__decoration", desktop=False)
    desktop = rules_for(rules, ".fc-about-cta__decoration", desktop=True)
    require(len(mobile) == 1 and mobile[0].get("display") == "none", "cta: side decorations must be mobile-hidden")
    require(len(desktop) == 1 and desktop[0].get("display") == "flex", "cta: side decorations must become visible at 1024px")


def validate_pins(paths: list[str]) -> None:
    for relative in paths:
        expected = PRODUCTION_SHA256[relative]
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        require(actual == expected, f"{relative}: production SHA-256 drifted (expected {expected}, got {actual})")


VALIDATORS = {"story": validate_story, "process": validate_process, "cta": validate_cta}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=tuple(CONTRACTS))
    args = parser.parse_args()
    selected = [args.section] if args.section else list(CONTRACTS)
    failures: list[str] = []

    for key in selected:
        contract = CONTRACTS[key]
        try:
            VALIDATORS[key](contract)
            validate_pins([contract["liquid"], contract["css"]])
            print(f"PASS {key}")
        except (OSError, ValidationError, TypeError, KeyError, ValueError) as exc:
            failures.append(f"FAIL {key}: {exc}")
            print(failures[-1])

    if failures:
        print(f"About sections B validation failed: {len(failures)} section(s).", file=sys.stderr)
        return 1
    print(f"About sections B validation passed: {len(selected)} section(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
