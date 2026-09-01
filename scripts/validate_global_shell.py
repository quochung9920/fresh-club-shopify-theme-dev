#!/usr/bin/env python3
"""Validate the Fresh Club global header/footer contract."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "docs/global-shell-contract.json").read_text(encoding="utf-8"))


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def css_rule_blocks(source: str, selector: str) -> list[str]:
    """Return exact selector blocks; decoy suffix/prefix selectors do not match."""
    return re.findall(rf"(?<![\w-]){re.escape(selector)}\s*\{{([^{{}}]*)\}}", source, flags=re.S)


def css_values(blocks: list[str], property_name: str) -> list[str]:
    values: list[str] = []
    for block in blocks:
        values.extend(value.strip() for value in re.findall(rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*([^;}}]+)", block))
    return values


errors: list[str] = []
layout = text(CONTRACT["scope"]["layout"])
header = text(CONTRACT["scope"]["header"])
search_row = text(CONTRACT["scope"]["search_row"])
footer = text(CONTRACT["scope"]["footer"])
social_icons = text("snippets/social-icons.liquid")
footer_group_source = text("sections/footer-group.json")
base_css_source = text("assets/base.css")
settings_schema_source = text("config/settings_schema.json")
interaction_contract_source = text("docs/about-us-native-refactor/contracts/interaction-contract.json")
header_group_source = text("sections/header-group.json")
search_form_js = text("assets/search-form.js")
predictive_search_js = text("assets/predictive-search.js")
behavior_test_source = text("scripts/test_global_shell_behavior.js")
css_path = ROOT / CONTRACT["scope"]["style_asset"]
behavior_asset = CONTRACT["scope"].get("behavior_asset")
js_path = ROOT / behavior_asset if behavior_asset else None

require("{% sections 'header-group' %}" in layout, "global header group must render from theme layout", errors)
require("{% sections 'footer-group' %}" in layout, "global footer group must render from theme layout", errors)
require("freshclub-global-shell.css" in layout, "theme layout must load global shell CSS", errors)
require("freshclub-global-shell.js" not in layout, "always-visible header must not load scroll-autohide behavior", errors)
require("snippets/header-search.liquid" not in interaction_contract_source, "frozen interaction authority must not reference the removed modal search", errors)
require("snippets/header-search-row.liquid" in interaction_contract_source, "interaction authority must retain the global search row", errors)
require("custom-element upgrades before descendant parsing" in interaction_contract_source and "without partial listeners" in interaction_contract_source, "interaction contract must require lifecycle-safe predictive-search upgrades", errors)
require("initializeSearchForm()" in search_form_js and "observeSearchInitialization" in search_form_js and "new MutationObserver" in search_form_js, "base search form must observe descendant completion before initialization", errors)
require("initializePredictiveSearch()" in predictive_search_js and "observeSearchInitialization(() => this.initializePredictiveSearch())" in predictive_search_js, "predictive search must observe descendant completion before initialization", errors)
require("predictive search must not throw when upgraded before all descendants are parsed" in behavior_test_source and "must not partially bind form listeners" in behavior_test_source, "behavior suite must cover parser-order predictive-search upgrades without partial listeners", errors)
require('"sticky_header_type"' not in header_group_source, "header group must not retain the removed sticky-mode setting", errors)
require(css_path.is_file(), "global shell CSS asset is missing", errors)
require(js_path is None, "always-visible header contract must not declare a behavior asset", errors)
require(not (ROOT / "assets/freshclub-global-shell.js").exists(), "scroll-autohide JS asset must be removed", errors)

require('data-fc-header-primary' in header, "header primary row marker is missing", errors)
require('<sticky-header' in header, "global shell must always render the native sticky-header element", errors)
require('data-sticky-type="always"' in header, "global shell must force row 1 to remain sticky", errors)
require("section.settings.sticky_header_type" not in header.split('<sticky-header', 1)[0][-500:], "global shell tag must not depend on merchant sticky mode", errors)
require('data-fc-header-secondary' in search_row, "header secondary row marker is missing", errors)
require("section.settings.menu" in header, "header must retain merchant menu authority", errors)
require("render 'header-drawer'" in header, "header must retain native mobile drawer", errors)
require("render 'header-search'" not in header, "row 1 must not duplicate the global predictive search", errors)
require("this.searchModal?.close(false)" in header, "sticky modes must tolerate the removed row-1 search modal", errors)
require("this.headerMediaQuery.removeEventListener('change', this.onHeaderBreakpointChange)" in header, "sticky header must clean up its breakpoint listener", errors)
require("routes.cart_url" in header, "header must retain native cart route", errors)
require("general.cart.view" in header, "cart link must expose an accessible name and item count", errors)
require("cart.total_price" in header, "header must retain live cart total", errors)
require("predictive-search" in search_row, "secondary row must retain predictive search", errors)
require("request.page_type != 'search'" in search_row, "global search must fall back to GET on the search template to prevent duplicate predictive-result IDs", errors)
require('method="get"' in search_row and "routes.search_url" in search_row, "search must retain GET fallback", errors)
require("contact_label" in search_row and "contact_link" in search_row, "contact control must be merchant-configurable", errors)

require("footer-menu" not in footer, "footer source must not hard-code the footer menu handle", errors)
require("block.settings.menu.links" in footer, "footer must retain merchant link-list authority", errors)
require("form 'customer'" in footer, "footer must retain native newsletter form", errors)
footer_field_start = footer.index('<div class="field">')
footer_button_start = footer.index('<button', footer_field_start)
require("</div>" not in footer[footer_field_start:footer_button_start], "Subscribe must remain inside the native newsletter field", errors)
require("render 'social-icons'" in footer, "footer must retain theme social settings", errors)
require("settings.social_linkedin_link == blank" in footer, "footer social eligibility must include LinkedIn", errors)
require("section.settings.newsletter_placeholder" in footer, "footer email placeholder must remain merchant-editable", errors)
require("section.settings.copyright_text" in footer, "footer copyright must remain merchant-editable", errors)
require('"id": "newsletter_placeholder"' in footer and '"default": "Enter your email"' in footer, "footer schema must default to the exact Figma email placeholder", errors)
require('"id": "copyright_text"' in footer and '"default": "© 2025 FreshClub. All rights reserved."' in footer, "footer schema must default to the exact Figma copyright", errors)
require('"newsletter_placeholder"' not in footer_group_source and '"copyright_text"' not in footer_group_source, "generated footer state must rely on schema defaults that Shopify preserves", errors)
require("social_linkedin_link" in settings_schema_source, "Theme Editor must expose a LinkedIn URL setting", errors)
require("settings.social_linkedin_link" in social_icons, "footer social list must conditionally render LinkedIn", errors)
require("icon-linkedin.svg" in social_icons, "footer LinkedIn control must use an accessible local icon", errors)
require(
    social_icons.index("settings.social_linkedin_link")
    < social_icons.index("settings.social_instagram_link")
    < social_icons.index("settings.social_facebook_link")
    < social_icons.index("settings.social_youtube_link"),
    "footer social authority must follow Figma order: LinkedIn, Instagram, Facebook, YouTube",
    errors,
)
require(
    re.search(r"\.button\s*\{[^}]*letter-spacing:\s*normal", base_css_source, flags=re.S) is not None,
    "global buttons must use exact Figma letter spacing while preserving existing hover",
    errors,
)
require(".button--primary:hover" in base_css_source and "translateY(-8px)" in base_css_source, "global primary hover must remain intact", errors)

for asset_name, expected_sha256 in CONTRACT.get("assets", {}).items():
    asset_path = ROOT / "assets" / asset_name
    require(asset_path.is_file(), f"required global shell asset is missing: {asset_name}", errors)
    if asset_path.is_file():
        actual_sha256 = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        require(actual_sha256 == expected_sha256, f"global shell asset hash changed: {asset_name}", errors)
require(
    header.count("freshclub-logo-header.png") == 2
    and re.search(r"(?<!section\.)settings\.logo(?:\b|_)", header.split("</sticky-header>", 1)[0]) is None,
    "header must always render the exact HTML-authority logo",
    errors,
)
authority_header_logos = [tag for tag in re.findall(r"<img\b[^>]*>", header, flags=re.S) if "freshclub-logo-header.png" in tag]
require(
    len(authority_header_logos) == 2
    and all(re.search(r'class="[^"]*\bheader__heading-logo\b[^"]*\bmotion-reduce\b[^"]*"', tag) for tag in authority_header_logos)
    and all('width="133"' in tag and 'height="32"' in tag and 'alt="FreshClub"' in tag and 'loading="eager"' in tag for tag in authority_header_logos),
    "both rendered header logo branches must bind the exact authority asset to required classes, dimensions, alt text, and loading behavior",
    errors,
)
require("freshclub-logo-footer.png" in footer and "settings.footer_logo" not in footer, "footer must always render the exact HTML-authority logo", errors)
require("fc-footer-brand" in footer and "fc-footer-logo" in footer, "footer logo must use footer-specific positioning classes", errors)
require("header__heading-logo-wrapper" not in footer and "header__heading-logo motion-reduce" not in footer, "footer logo must not inherit header positioning classes", errors)
require(
    footer.index("fc-footer-brand") < footer.index("{%- if section.blocks.size > 0 -%}"),
    "footer authority logo must render even when the section has no blocks",
    errors,
)
require("fc-icon-menu-html.svg" in text("snippets/header-drawer.liquid"), "mobile drawer must use the exact HTML menu icon", errors)
require("fc-icon-search-html.svg" in search_row, "global search must use the exact HTML search icon", errors)
require(header.count("fc-icon-cart-html.svg") == 1, "native cart control must use exactly one HTML-authority cart icon", errors)

if css_path.is_file():
    css = css_path.read_text(encoding="utf-8")
    require(
        hashlib.sha256(css.encode("utf-8")).hexdigest() == "29735e0841cc4a712d28d58e28b2ea225d68d420d4f8f26bac888fb4d9038438",
        "global shell CSS byte drift: exact reviewed cascade required",
        errors,
    )
    for token in ("#16494a", "#ea1a65", "#f5faf3", "Lexend Deca", "DM Sans"):
        require(token.lower() in css.lower(), f"global shell CSS missing token: {token}", errors)
    require("--font-body-family" not in css, "global shell must not override merchant typography variables", errors)
    require(re.search(r"(?m)^html,\s*$", css) is None, "global shell typography must not target the whole document", errors)
    require(
        re.search(r"\[data-fc-header-shell\],\s*\[data-fc-global-footer\]\s*\{[^}]*font-family:\s*'Lexend Deca'", css, flags=re.S)
        is not None,
        "Fresh Club typography must be scoped to the global shell",
        errors,
    )
    require("[data-fc-header-primary]" in css, "CSS missing primary-row contract selector", errors)
    require("[data-fc-header-secondary]" in css, "CSS missing secondary-row contract selector", errors)
    cart_badge_blocks = css_rule_blocks(css, "[data-fc-header-primary] .cart-count-bubble")
    for property_name, expected in (("display", ["grid"]), ("place-items", ["center"]), ("line-height", ["1"]), ("padding", ["0"]), ("text-align", ["center"])):
        require(
            css_values(cart_badge_blocks, property_name) == expected,
            f"cart count badge must center its number with {property_name}: {expected[0]}",
            errors,
        )
    require("fc-secondary-hidden" not in css, "CSS must not contain a secondary-row hidden state", errors)
    secondary_blocks = css_rule_blocks(css, "[data-fc-header-secondary]")
    require(len(secondary_blocks) == 2, "secondary row must have exactly base and desktop scoped rules", errors)
    require(css_values(secondary_blocks, "transform") == ["translateY(0)"], "secondary row transform must remain visibly neutral", errors)
    require(css_values(secondary_blocks, "opacity") == ["1"], "secondary row opacity must remain visible", errors)
    require(css_values(secondary_blocks, "overflow") == ["visible"], "secondary row overflow must not collapse content", errors)
    require(css_values(secondary_blocks, "max-height") == ["72px", "100px"], "secondary row heights must remain visible at base and desktop breakpoints", errors)
    require(not css_values(secondary_blocks, "transition"), "secondary row must not animate or auto-hide", errors)
    require(
        re.search(r"\.fc-header-search-row\s*\{[^}]*margin-inline:\s*auto", css, flags=re.S) is not None,
        "page-width fc-header-search-row must be exactly centered",
        errors,
    )
    require(
        re.search(r"\.fc-header-search-actions\s*\{[^}]*margin-inline:\s*auto", css, flags=re.S) is not None,
        "search/contact action group must remain centered inside its row",
        errors,
    )
    require(
        re.search(r"grid-template-columns:\s*minmax\(0, 1fr\)\s+minmax\(0, 480px\)\s+minmax\(0, 1fr\)", css) is not None,
        "desktop search row must use symmetric columns around the centered 480px search field",
        errors,
    )
    require(
        re.search(r"predictive-search,\s*\.fc-header-search-actions search-form\s*\{[^}]*grid-column:\s*2", css, flags=re.S) is not None,
        "desktop predictive/GET search must occupy the exact center column",
        errors,
    )
    require(
        re.search(r"\.fc-header-contact\s*\{[^}]*grid-column:\s*3[^}]*justify-self:\s*end", css, flags=re.S) is not None,
        "desktop Contact Us must be anchored to the right column",
        errors,
    )
    contact_blocks = css_rule_blocks(css, ".fc-header-contact")
    for property_name in ("min-height", "padding", "border-radius", "font-size", "font-weight", "line-height", "background", "color"):
        require(
            not css_values(contact_blocks, property_name),
            f"Contact Us must inherit standard button {property_name} instead of overriding it",
            errors,
        )
    require(".fc-header-contact:hover" not in css, "Contact Us must inherit the standard primary-button hover", errors)
    require(".fc-header-search-spacer" not in css, "asymmetric search spacer must be removed", errors)
    require(
        re.search(r"\.fc-footer-brand\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*align-items:\s*flex-start[^}]*gap:\s*32px", css, flags=re.S) is not None,
        "footer brand must pin the logo and navigation to the left in HTML-authority order",
        errors,
    )
    require(
        "flex-start" in css_values(css_rule_blocks(css, "[data-fc-global-footer] .footer__content-top .footer__blocks-wrapper"), "align-items"),
        "footer blocks wrapper must override the native centered grid alignment",
        errors,
    )
    footer_label_blocks = css_rule_blocks(css, "[data-fc-global-footer] .newsletter-form__field-wrapper .field__label")
    for property_name, expected in (("top", ["50%"]), ("left", ["14px"]), ("transform", ["translateY(-50%)"]), ("font-size", ["14px"]), ("line-height", ["1.4"])):
        require(css_values(footer_label_blocks, property_name) == expected, f"footer resting newsletter label must use {property_name}: {expected[0]}", errors)
    floating_label_match = re.search(r"\[data-fc-global-footer\] \.field__input:focus ~ \.field__label,\s*\[data-fc-global-footer\] \.field__input:not\(:placeholder-shown\) ~ \.field__label,\s*\[data-fc-global-footer\] \.field__input:-webkit-autofill ~ \.field__label\s*\{([^{}]*)\}", css, flags=re.S)
    floating_label_blocks = [floating_label_match.group(1)] if floating_label_match else []
    for property_name, expected in (("font-size", ["10px"]), ("top", ["6px"]), ("left", ["14px"]), ("transform", ["none"]), ("line-height", ["14px"])):
        require(css_values(floating_label_blocks, property_name) == expected, f"footer floating newsletter label must use {property_name}: {expected[0]}", errors)
    floating_input_match = re.search(r"\[data-fc-global-footer\] \.field__input:focus,\s*\[data-fc-global-footer\] \.field__input:not\(:placeholder-shown\),\s*\[data-fc-global-footer\] \.field__input:-webkit-autofill\s*\{([^{}]*)\}", css, flags=re.S)
    floating_input_blocks = [floating_input_match.group(1)] if floating_input_match else []
    require(css_values(floating_input_blocks, "padding") == ["20px 14px 6px"], "footer input value must move below its floating label", errors)
    search_placeholder_blocks = css_rule_blocks(css, ".fc-header-search-actions .search__input::placeholder")
    require(css_values(search_placeholder_blocks, "opacity") == ["0"], "header search must use its associated label instead of a visible native placeholder", errors)
    search_label_blocks = css_rule_blocks(css, ".fc-header-search-actions .field__label")
    for property_name, expected in (("display", ["block"]), ("top", ["50%"]), ("left", ["16px"]), ("transform", ["translateY(-50%)"]), ("font-size", ["16px"]), ("line-height", ["24px"])):
        require(css_values(search_label_blocks, property_name) == expected, f"header resting search label must use {property_name}: {expected[0]}", errors)
    search_floating_match = re.search(r"\.fc-header-search-actions \.search__input:focus ~ \.field__label,\s*\.fc-header-search-actions \.search__input:not\(:placeholder-shown\) ~ \.field__label,\s*\.fc-header-search-actions \.search__input:-webkit-autofill ~ \.field__label\s*\{([^{}]*)\}", css, flags=re.S)
    search_floating_blocks = [search_floating_match.group(1)] if search_floating_match else []
    for property_name, expected in (("font-size", ["10px"]), ("top", ["6px"]), ("left", ["16px"]), ("transform", ["none"]), ("line-height", ["14px"])):
        require(css_values(search_floating_blocks, property_name) == expected, f"header floating search label must use {property_name}: {expected[0]}", errors)
    search_input_match = re.search(r"\.fc-header-search-actions \.search__input:focus,\s*\.fc-header-search-actions \.search__input:not\(:placeholder-shown\),\s*\.fc-header-search-actions \.search__input:-webkit-autofill\s*\{([^{}]*)\}", css, flags=re.S)
    search_input_blocks = [search_input_match.group(1)] if search_input_match else []
    require(css_values(search_input_blocks, "padding") == ["20px 52px 4px 16px"], "header search query must move below its floating label", errors)
    require(
        re.search(r"\.fc-footer-logo\s*\{[^}]*display:\s*block[^}]*width:\s*169px[^}]*height:\s*41px[^}]*object-position:\s*left center", css, flags=re.S) is not None,
        "footer logo must render at the HTML-authority size and left position",
        errors,
    )
    newsletter_button_blocks = css_rule_blocks(css, "[data-fc-global-footer] .newsletter-form__button")
    require(
        len(newsletter_button_blocks) == 1 and css_values(newsletter_button_blocks, "position") == ["relative"],
        "newsletter button must contain its pseudo-element instead of painting a pink border around the form",
        errors,
    )
    require(
        re.search(r"\[data-fc-global-footer\]\.footer\s*\{[^}]*padding:\s*44px 20px", css, flags=re.S)
        is not None,
        "global footer padding must outrank section-instance padding",
        errors,
    )
    require(
        re.search(r"\.footer__content-top\s*\{[^}]*flex-direction:\s*column[^}]*gap:\s*24px[^}]*padding:\s*0 0 8px[^}]*border-bottom:\s*1px solid rgba\(255, 255, 255, 0\.08\)", css, flags=re.S) is not None,
        "mobile footer top group must match Figma column, gap, padding, and divider",
        errors,
    )
    require(
        re.search(r"\.footer__content-top \.footer__blocks-wrapper\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*gap:\s*32px", css, flags=re.S) is not None,
        "footer wrapper must outrank the native grid and preserve the 32px logo-to-menu gap",
        errors,
    )
    require(
        re.search(r"\.footer-block--menu \.footer-block__details-content\s*\{[^}]*display:\s*flex[^}]*flex-direction:\s*row[^}]*flex-wrap:\s*nowrap[^}]*gap:\s*40px", css, flags=re.S) is not None,
        "footer navigation must remain one left-aligned row with a 40px Figma gap",
        errors,
    )
    require(
        re.search(r"\.footer__content-top \.footer-block--menu\s*\{[^}]*margin:\s*0", css, flags=re.S) is not None,
        "footer menu block must outrank native mobile margins",
        errors,
    )
    require(
        re.search(r"\.newsletter-form__field-wrapper \.field\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto[^}]*gap:\s*16px[^}]*height:\s*48px", css, flags=re.S) is not None,
        "footer email capture must keep the Figma input/button row",
        errors,
    )
    for selector in (
        "[data-fc-global-footer] .newsletter-form__field-wrapper .field__input",
        "[data-fc-global-footer] .newsletter-form__field-wrapper .field__label",
        "[data-fc-global-footer] .newsletter-form__button",
    ):
        require("1" in css_values(css_rule_blocks(css, selector), "grid-row"), f"footer email capture child must stay on row 1: {selector}", errors)
    for selector in (
        "[data-fc-global-footer] .newsletter-form__field-wrapper .field__input",
        "[data-fc-global-footer] .newsletter-form__button",
    ):
        blocks = css_rule_blocks(css, selector)
        require("border-box" in css_values(blocks, "box-sizing"), f"footer control must include borders inside its exact 48px height: {selector}", errors)
        require("0" in css_values(blocks, "margin"), f"footer control must not shift off the shared grid row: {selector}", errors)
    require(
        re.search(r"\.scroll-trigger\.animate--slide-in\s*\{[^}]*opacity:\s*1[^}]*transform:\s*none[^}]*animation:\s*none", css, flags=re.S) is not None,
        "footer geometry must not be displaced by the global reveal animation",
        errors,
    )
    require(
        "grid-template-columns: minmax(0, 1fr) 375px" in css,
        "desktop footer must reserve the exact 375px newsletter column",
        errors,
    )
    require(
        re.search(r"\.footer__content-bottom-wrapper\s*\{[^}]*padding-top:\s*28px[^}]*border-top:\s*0", css, flags=re.S) is not None,
        "mobile footer bottom group must begin 28px after the top divider",
        errors,
    )
    require(
        re.search(r"\.copyright__content\s*\{[^}]*display:\s*block[^}]*line-height:\s*24px", css, flags=re.S) is not None,
        "footer copyright must occupy the exact 24px Figma line box",
        errors,
    )
    require(
        re.search(
            r"\.fc-header-search-actions predictive-search,\s*\.fc-header-search-actions search-form\s*\{[^}]*position:\s*relative",
            css,
            flags=re.S,
        )
        is not None,
        "predictive search must establish a local positioning context",
        errors,
    )
    mobile_contract_start = "@media screen and (max-width: 989px) {"
    mobile_contract_end = "@media screen and (max-width: 749px) {"
    require(mobile_contract_start in css, "CSS missing mobile header contract", errors)
    if mobile_contract_start in css:
        mobile_css = css.split(mobile_contract_start, 1)[1].split(mobile_contract_end, 1)[0]
        require(
            re.search(r"header__icon--cart\s*\{[^}]*width:\s*48px", mobile_css, flags=re.S) is not None,
            "mobile cart must compact to a 48px touch target",
            errors,
        )
        require(
            re.search(r"cart-total-price\s*\{[^}]*display:\s*none", mobile_css, flags=re.S) is not None,
            "mobile cart must hide the desktop total to prevent 375px overflow",
            errors,
        )

require("always-visible header has no autohide behavior asset" in behavior_test_source, "behavior suite must enforce the no-autohide contract", errors)

schema_match = re.search(r"{% schema %}\s*(\{.*\})\s*{% endschema %}", header, flags=re.S)
require(schema_match is not None, "header schema is missing or unreadable", errors)
if schema_match:
    try:
        schema = json.loads(schema_match.group(1))
        setting_ids = {item.get("id") for item in schema.get("settings", [])}
        require("sticky_header_type" not in setting_ids, "fixed global sticky behavior must not expose a contradictory merchant control", errors)
        require("contact_label" in setting_ids, "header schema missing contact_label", errors)
        require("contact_link" in setting_ids, "header schema missing contact_link", errors)
        require("search_placeholder" in setting_ids, "header schema missing search_placeholder", errors)
    except json.JSONDecodeError as exc:
        errors.append(f"header schema is invalid JSON: {exc}")

if errors:
    print("Global shell contract validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("Global shell contract validation passed")
print("Global header/footer authority: native Shopify")
print("Full two-row header: always sticky and always visible")
print("Search row: exactly centered at every breakpoint")
