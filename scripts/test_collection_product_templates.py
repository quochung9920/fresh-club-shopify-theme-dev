from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_shopify_json(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("{") :])


class CollectionProductTemplateTests(unittest.TestCase):
    def test_collection_mobile_uses_one_card_per_row(self) -> None:
        template = load_shopify_json(ROOT / "templates" / "collection.json")
        settings = template["sections"]["product-grid"]["settings"]
        css = (ROOT / "assets" / "template-collection.css").read_text(encoding="utf-8")

        self.assertEqual(settings["columns_mobile"], "1")
        self.assertRegex(
            css,
            re.compile(
                r"@media screen and \(max-width: 749px\).*?"
                r"\.fc-collection-figma .*?#product-grid > \.grid__item\s*\{[^}]*"
                r"(?:flex-basis|width):\s*100%",
                re.DOTALL,
            ),
        )

    def test_collection_curve_selector_is_valid_class_selector(self) -> None:
        liquid = (ROOT / "sections" / "main-collection-product-grid.liquid").read_text(encoding="utf-8")
        self.assertNotIn(",curved-section", liquid)
        self.assertIn(".section-{{ section.id }}-padding.curved-section", liquid)

    def test_collection_list_is_disabled_in_figma_default_composition(self) -> None:
        template = load_shopify_json(ROOT / "templates" / "collection.json")
        collection_list = next(section for section in template["sections"].values() if section["type"] == "collection_list")
        self.assertIs(collection_list.get("disabled"), True)

    def test_collection_desktop_matches_figma_grid_geometry(self) -> None:
        template = load_shopify_json(ROOT / "templates" / "collection.json")
        settings = template["sections"]["product-grid"]["settings"]
        css = (ROOT / "assets" / "template-collection.css").read_text(encoding="utf-8")

        self.assertEqual(settings["products_per_page"], 12)
        self.assertEqual(settings["columns_desktop"], 4)
        for contract in (
            "--fc-collection-content: 128rem",
            "--fc-collection-card: 29.6rem",
            "--fc-collection-gap: 3.2rem",
        ):
            self.assertIn(contract, css)
        self.assertRegex(css, r"\.fc-collection-figma \.product-grid\s*\{")
        self.assertIn("calc((100% - (3 * var(--fc-collection-gap))) / 4)", css)
        self.assertIn("margin: 0", (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8").lower())

    def test_collection_cards_match_figma_visual_tokens(self) -> None:
        css = (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8").lower()
        required = (
            "border: 1px solid #d8ebd0",
            "border-radius: 0.8rem",
            "height: 12rem",
            "grid-template-rows: 0 4rem 0 8rem",
            "quick-add__submit",
            "font-size: 1.8rem",
            "letter-spacing: -0.07802rem",
            ".unit-price",
            "font-size: 1.2rem",
            "color: #94969c",
            "background: #ea1a65",
            "quantity-input-custom",
        )
        for token in required:
            self.assertIn(token, css)

    def test_collection_faq_reuses_how_it_works_faq_component(self) -> None:
        collection = load_shopify_json(ROOT / "templates" / "collection.json")
        how_it_works = load_shopify_json(ROOT / "templates" / "page.how-does-it-work.json")
        collection_faq = collection["sections"]["collapsible_content_pnW7dG"]
        how_faq = how_it_works["sections"]["how_faq"]
        component = (ROOT / "sections" / "fc-how-faq.liquid").read_text(encoding="utf-8")
        collection_css = (ROOT / "assets" / "template-collection.css").read_text(encoding="utf-8")
        generic_accordion = (ROOT / "sections" / "collapsible-content.liquid").read_text(encoding="utf-8")

        self.assertEqual(collection_faq["type"], how_faq["type"])
        self.assertEqual(collection_faq["type"], "fc-how-faq")
        self.assertTrue(collection_faq["settings"]["heading"])
        self.assertTrue(collection_faq["blocks"])
        self.assertTrue(all(block["type"] == "faq" for block in collection_faq["blocks"].values()))
        for block in collection_faq["blocks"].values():
            self.assertEqual(set(block["settings"]), {"heading", "answer", "open_by_default"})
        first_block = collection_faq["blocks"][collection_faq["block_order"][0]]
        self.assertIs(first_block["settings"]["open_by_default"], True)
        self.assertIn("fc-how-faq.css", component)
        self.assertNotIn("fc-collection-faq", collection_css)
        self.assertNotIn("fresh_club_collection_style", generic_accordion)

    def test_both_templates_load_shared_figma_product_cards(self) -> None:
        collection = (ROOT / "sections" / "main-collection-product-grid.liquid").read_text(encoding="utf-8")
        related = (ROOT / "sections" / "related-products.liquid").read_text(encoding="utf-8")
        shared_path = ROOT / "assets" / "freshclub-product-card.css"

        self.assertIn("freshclub-product-card.css", collection)
        self.assertIn("freshclub-product-card.css", related)
        self.assertTrue(shared_path.is_file())
        shared = shared_path.read_text(encoding="utf-8").lower()
        for token in (
            ":is(.fc-collection-figma, .related-products)",
            "border-radius: 0.8rem",
            "background: #ea1a65",
            "quantity-input-custom",
        ):
            self.assertIn(token, shared)

    def test_collection_card_uses_requested_figma_wishlist_and_control_composition(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        quantity = (ROOT / "snippets" / "quantity-input-custom.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8").lower()
        contract = json.loads((ROOT / "docs" / "collection" / "interaction-contract.json").read_text(encoding="utf-8"))

        self.assertIn('class="fc-product-card__wishlist"', card)
        self.assertIn("render 'icon-heart-outline'", card)
        self.assertEqual(contract["wishlist"]["status"], "visual-only")
        self.assertEqual(contract["wishlist"]["interaction"], "non-interactive")
        self.assertNotIn("<button", card.split('class="fc-product-card__wishlist"', 1)[1].split("</span>", 1)[0])
        self.assertIn("render 'icon-cart-form'", quantity)
        self.assertIn("grid-template-columns: minmax(0, 1fr) auto", css)
        self.assertRegex(
            css,
            re.compile(r"\.quantity-input\s*\{[^}]*grid-column:\s*2", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(r"\.submit_btn\s*\{[^}]*grid-column:\s*1\s*/\s*-1", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.fc-collection-figma quantity-input-custom\.cart-quantity\s*\{[^}]*display:\s*contents",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(r"\.quantity-input\s*\{[^}]*position:\s*relative[^}]*z-index:\s*2", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(r"\.submit_btn\s*\{[^}]*position:\s*relative[^}]*z-index:\s*2", re.DOTALL),
        )
        self.assertNotRegex(
            css,
            re.compile(
                r":is\(\.fc-collection-figma, \.related-products\) quantity-input-custom\s*\{[^}]*display:\s*flex",
                re.DOTALL,
            ),
        )

    def test_ripeness_products_use_required_quick_add_modal(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        quantity = (ROOT / "snippets" / "quantity-input-custom.liquid").read_text(encoding="utf-8")
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")
        quick_add_css = (ROOT / "assets" / "quick-add.css").read_text(encoding="utf-8")
        collection = (ROOT / "sections" / "main-collection-product-grid.liquid").read_text(encoding="utf-8")
        featured = (ROOT / "sections" / "featured-collection.liquid").read_text(encoding="utf-8")
        related = (ROOT / "sections" / "related-products.liquid").read_text(encoding="utf-8")

        self.assertIn(
            "assign ripeness_options = card_product.metafields.custom.ripeness_options.value",
            card,
        )
        self.assertRegex(
            card,
            re.compile(
                r"if ripeness_options != blank\s+"
                r"if quick_add == 'standard' or quick_add == 'bulk'\s+"
                r"assign has_ripeness_quick_add = true"
            ),
        )
        self.assertIn("{% if has_ripeness_quick_add %}", card)
        self.assertIn("{% elsif quick_add == 'standard' %}", card)
        self.assertIn("{% elsif quick_add == 'bulk' %}", card)

        ripeness_branch = card.split("{% if has_ripeness_quick_add %}", 1)[1].split(
            "{% elsif quick_add == 'standard' %}", 1
        )[0]
        self.assertIn("{% if card_product.available %}", ripeness_branch)
        self.assertIn("{% if quick_add == 'bulk' %}", ripeness_branch)
        self.assertIn("modal_id: ripeness_modal_id", ripeness_branch)
        self.assertIn("min: ripeness_min", ripeness_branch)
        self.assertIn('<div class="quick-add no-js-hidden ripeness-quick-add-trigger">', ripeness_branch)
        self.assertIn('class="quick-add-modal no-js-hidden"', ripeness_branch)
        self.assertIn("<noscript>", ripeness_branch)
        self.assertIn(".ripeness-quick-add-trigger", ripeness_branch)
        self.assertIn('data-ripeness-modal="#{{ ripeness_modal_id }}"', ripeness_branch)
        self.assertIn('data-ripeness-static', ripeness_branch)
        self.assertIn("{{ 'products.product.add_to_cart' | t }}", ripeness_branch)
        self.assertIn('<quick-add-modal id="{{ ripeness_modal_id }}"', ripeness_branch)
        self.assertIn('class="ripeness-quick-add__content"', ripeness_branch)
        self.assertIn("<product-form", ripeness_branch)
        self.assertIn('name="id"', ripeness_branch)
        self.assertIn('name="quantity"', ripeness_branch)
        self.assertIn('name="properties[Ripeness preference]"', ripeness_branch)
        self.assertIn("{% for ripeness_option in ripeness_options %}", ripeness_branch)
        self.assertIn("required", ripeness_branch)
        self.assertIn('role="dialog"', ripeness_branch)
        self.assertIn('aria-modal="true"', ripeness_branch)
        self.assertIn('id="ModalClose-Ripeness-{{ card_product.id }}-{{ section_id }}"', ripeness_branch)
        self.assertRegex(ripeness_branch, re.compile(r"<button[^>]*disabled", re.DOTALL))
        self.assertIn("{{ 'products.product.sold_out' | t }}", ripeness_branch)
        self.assertNotIn("<quick-add-bulk", ripeness_branch)
        self.assertNotIn("Choose ripeness", ripeness_branch)
        self.assertNotRegex(ripeness_branch, re.compile(r'<a[^>]*href="{{ card_product\.url }}"', re.DOTALL))

        self.assertIn("{% if modal_id != blank %}", quantity)
        self.assertIn("{% if modal_id != blank %} no-js-hidden{% endif %}", quantity)
        self.assertIn("{% if modal_id != blank %} ripeness-quick-add-trigger{% endif %}", quantity)
        self.assertIn('data-ripeness-modal="#{{ modal_id }}"', quantity)
        self.assertNotIn('data-product-url="{{ product_url }}"', quantity)
        self.assertIn("button.dataset.ripenessModal", quick_add_js)
        self.assertIn("modal.show(button)", quick_add_js)
        self.assertIn("this.hasAttribute('data-ripeness-static')", quick_add_js)
        self.assertIn("this.modalContent.querySelector('form')?.reset()", quick_add_js)
        self.assertIn("sourceQuantity", quick_add_js)
        self.assertIn("modalQuantity", quick_add_js)
        self.assertIn(".ripeness-quick-add__content", quick_add_css)
        self.assertRegex(
            quick_add_css,
            re.compile(r"\.ripeness-quick-add__content product-form\s*\{[^}]*display:\s*block", re.DOTALL),
        )

        for section_source in (collection, featured, related):
            self.assertIn("quick-add.js", section_source)
            self.assertIn("product-form.js", section_source)

    def test_ripeness_dropdown_uses_accessible_custom_listbox(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")
        ripeness_branch = card.split("{% if has_ripeness_quick_add %}", 1)[1].split(
            "{% elsif quick_add == 'standard' %}", 1
        )[0]

        self.assertIn("<ripeness-select", ripeness_branch)
        self.assertIn('for="RipenessQuickAddTrigger-{{ card_product.id }}-{{ section_id }}"', ripeness_branch)
        self.assertIn('class="ripeness-select__native visually-hidden"', ripeness_branch)
        self.assertIn('name="properties[Ripeness preference]"', ripeness_branch)
        self.assertIn("required", ripeness_branch)
        self.assertIn('data-ripeness-select-trigger', ripeness_branch)
        self.assertIn('aria-haspopup="listbox"', ripeness_branch)
        self.assertIn('aria-expanded="false"', ripeness_branch)
        self.assertIn('role="listbox"', ripeness_branch)
        self.assertIn('aria-hidden="true"', ripeness_branch)
        self.assertIn('role="option"', ripeness_branch)
        self.assertIn('aria-selected="false"', ripeness_branch)
        self.assertIn("{% for ripeness_option in ripeness_options %}", ripeness_branch)
        self.assertIn('data-ripeness-submit', ripeness_branch)
        self.assertRegex(
            ripeness_branch,
            re.compile(r'<button[^>]*data-ripeness-submit[^>]*aria-disabled="true"', re.DOTALL),
        )
        self.assertNotRegex(ripeness_branch, re.compile(r"data-ripeness-submit[^>]*\sdisabled(?:\s|>)", re.DOTALL))

        self.assertIn("customElements.get('ripeness-select')", quick_add_js)
        self.assertIn("this.nativeSelect.value = option.dataset.value", quick_add_js)
        self.assertIn("new Event('change', { bubbles: true })", quick_add_js)
        self.assertIn("this.submitButton.setAttribute('aria-disabled', String(!this.nativeSelect.value))", quick_add_js)
        self.assertIn("this.form.addEventListener('reset'", quick_add_js)
        self.assertIn("this.nativeSelect.addEventListener('change'", quick_add_js)
        self.assertIn("document.addEventListener('click'", quick_add_js)
        for key in ("ArrowDown", "ArrowUp", "Home", "End", "Escape", "Enter", " "):
            self.assertIn(f"case '{key}':", quick_add_js)

    def test_ripeness_modal_matches_fresh_club_visual_contract(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "quick-add.css").read_text(encoding="utf-8")

        self.assertIn("quick-add-modal__content--ripeness", card)
        self.assertRegex(
            css,
            re.compile(
                r"quick-add-modal\[data-ripeness-static\] \.quick-add-modal__content--ripeness\s*\{"
                r"[^}]*max-width:\s*52rem[^}]*border:\s*1px solid #d8ebd0"
                r"[^}]*border-radius:\s*1\.6rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.ripeness-select__trigger\s*\{"
                r"[^}]*position:\s*relative[^}]*min-height:\s*5rem"
                r"[^}]*border:\s*1px solid #d8ebd0[^}]*border-radius:\s*0\.8rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.ripeness-quick-add__content \.product-form__submit\s*\{"
                r"[^}]*background:\s*#e51963[^}]*border-radius:\s*0\.8rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"@media screen and \(max-width:\s*749px\)\s*\{[^}]*"
                r"quick-add-modal\[data-ripeness-static\] \.quick-add-modal__content--ripeness\s*\{"
                r"[^}]*bottom:\s*1\.2rem",
                re.DOTALL,
            ),
        )

    def test_ripeness_custom_listbox_is_polished_and_responsive(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "quick-add.css").read_text(encoding="utf-8")

        self.assertIn('class="ripeness-select__value"', card)
        self.assertIn('class="ripeness-select__option-text"', card)
        self.assertRegex(
            css,
            re.compile(
                r"\.ripeness-select__listbox\s*\{"
                r"[^}]*max-height:\s*0[^}]*opacity:\s*0[^}]*overflow-y:\s*auto"
                r"[^}]*transition:",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"ripeness-select\[open\] \.ripeness-select__listbox\s*\{"
                r"[^}]*max-height:\s*22rem[^}]*opacity:\s*1",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.ripeness-select__option\s*\{"
                r"[^}]*min-height:\s*4\.4rem[^}]*border-radius:\s*0\.6rem",
                re.DOTALL,
            ),
        )
        self.assertIn('.ripeness-select__option[aria-selected="true"]', css)
        self.assertIn(".ripeness-select__option:focus-visible", css)
        self.assertRegex(
            css,
            re.compile(
                r"\.ripeness-select__value,\s*\.ripeness-select__option-text\s*\{"
                r"[^}]*min-width:\s*0[^}]*overflow-wrap:\s*anywhere",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"@media screen and \(max-width:\s*749px\)\s*\{[^}]*"
                r"ripeness-select\[open\] \.ripeness-select__listbox\s*\{"
                r"[^}]*max-height:\s*min\(20rem, 32vh\)",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"@media \(prefers-reduced-motion:\s*reduce\)\s*\{[^}]*"
                r"\.ripeness-select__listbox",
                re.DOTALL,
            ),
        )

    def test_ripeness_dropdown_escape_does_not_close_parent_modal(self) -> None:
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")

        self.assertIn("this.suppressModalEscape = true", quick_add_js)
        self.assertIn("this.addEventListener('keyup', this.onKeyup)", quick_add_js)
        self.assertIn("this.removeEventListener('keyup', this.onKeyup)", quick_add_js)
        self.assertRegex(
            quick_add_js,
            re.compile(
                r"onKeyup\(event\)\s*\{[^}]*event\.code\.toUpperCase\(\) !== 'ESCAPE'"
                r"[^}]*event\.stopPropagation\(\)",
                re.DOTALL,
            ),
        )

    def test_ripeness_dropdown_closes_and_resets_with_modal_form(self) -> None:
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")

        self.assertRegex(
            quick_add_js,
            re.compile(
                r"this\.onFormReset\s*=\s*\(\)\s*=>\s*requestAnimationFrame\(\(\)\s*=>\s*\{"
                r"[^}]*this\.syncFromNative\(\)[^}]*this\.close\(\)",
                re.DOTALL,
            ),
        )

    def test_ripeness_dropdown_does_not_refocus_an_option_after_close(self) -> None:
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")

        self.assertRegex(
            quick_add_js,
            re.compile(
                r"requestAnimationFrame\(\(\)\s*=>\s*\{"
                r"[^}]*if \(this\.hasAttribute\('open'\)\) this\.focusOption\(targetIndex\)",
                re.DOTALL,
            ),
        )

    def test_ripeness_dropdown_initializes_after_dynamic_section_markup_is_ready(self) -> None:
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")
        constructor = quick_add_js.split("constructor() {", 1)[1].split("connectedCallback()", 1)[0]

        self.assertNotIn("querySelector", constructor)
        self.assertNotIn("closest('form')", constructor)
        self.assertIn("if (this.initialize()) return", quick_add_js)
        self.assertIn("this.pendingObserver = new MutationObserver", quick_add_js)
        self.assertIn("this.pendingObserver.observe(this.closest('form') || this", quick_add_js)
        self.assertIn("initialize() {", quick_add_js)
        self.assertIn("if (!nativeSelect || !trigger || !value || !listbox || !form || !submitButton || !options.length)", quick_add_js)
        self.assertIn("this.initialized = true", quick_add_js)
        self.assertIn("this.pendingObserver?.disconnect()", quick_add_js)
        self.assertIn("this.initialized = false", quick_add_js)

    def test_ripeness_dropdown_preserves_empty_submit_state_after_late_form_completion(self) -> None:
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")

        self.assertIn("this.submitStateObserver = new MutationObserver", quick_add_js)
        self.assertIn("if (!this.nativeSelect.value && this.submitButton.getAttribute('aria-disabled') !== 'true')", quick_add_js)
        self.assertIn("this.submitStateObserver.observe(this.submitButton", quick_add_js)
        self.assertIn("attributeFilter: ['aria-disabled']", quick_add_js)
        self.assertIn("this.submitStateObserver?.disconnect()", quick_add_js)

    def test_ripeness_modal_initial_focus_uses_cached_focus_trap_boundary(self) -> None:
        quick_add_js = (ROOT / "assets" / "quick-add.js").read_text(encoding="utf-8")
        static_show = quick_add_js.split("if (this.hasAttribute('data-ripeness-static'))", 2)[2].split(
            "opener.setAttribute('aria-disabled'", 1
        )[0]

        self.assertIn("super.show(opener)", static_show)
        self.assertIn("this.querySelector('[id^=\"ModalClose-Ripeness-\"]')?.focus()", static_show)

    def test_ripeness_modal_button_contrast_meets_wcag_aa(self) -> None:
        css = (ROOT / "assets" / "quick-add.css").read_text(encoding="utf-8")
        button_rule = re.search(
            r"\.ripeness-quick-add__content \.product-form__submit\s*\{(?P<body>[^}]*)\}",
            css,
            re.DOTALL,
        )
        if button_rule is None:
            self.fail("missing Ripeness submit button rule")

        def parse_hex(value: str) -> tuple[int, int, int]:
            value = value.lstrip("#")
            if len(value) == 3:
                value = "".join(character * 2 for character in value)
            return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))

        def luminance(color: tuple[int, int, int]) -> float:
            channels = [channel / 255 for channel in color]
            linear = [
                channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        body = button_rule.group("body")
        background = re.search(r"background:\s*(#[0-9a-fA-F]{3,6})", body)
        foreground = re.search(r"color:\s*(#[0-9a-fA-F]{3,6})", body)
        if background is None or foreground is None:
            self.fail("Ripeness submit button must define hex background and foreground colors")
        lighter, darker = sorted(
            (luminance(parse_hex(background.group(1))), luminance(parse_hex(foreground.group(1)))),
            reverse=True,
        )
        self.assertGreaterEqual((lighter + 0.05) / (darker + 0.05), 4.5)

    def test_ripeness_modal_motion_is_smooth_and_reduced_motion_safe(self) -> None:
        css = (ROOT / "assets" / "quick-add.css").read_text(encoding="utf-8")

        self.assertRegex(
            css,
            re.compile(
                r"quick-add-modal\[data-ripeness-static\]\s*\{"
                r"[^}]*transition:\s*opacity var\(--duration-medium\)",
                re.DOTALL,
            ),
        )
        self.assertIn("quick-add-modal[data-ripeness-static][open] .quick-add-modal__content--ripeness", css)
        self.assertRegex(
            css,
            re.compile(
                r"quick-add-modal\[data-ripeness-static\]\s*\{[^}]*pointer-events:\s*none",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"quick-add-modal\[data-ripeness-static\]\[open\]\s*\{[^}]*pointer-events:\s*auto",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"@media \(prefers-reduced-motion:\s*reduce\)\s*\{[^}]*"
                r"quick-add-modal\[data-ripeness-static\]",
                re.DOTALL,
            ),
        )

    def test_collection_card_preserves_media_stage_when_product_has_no_featured_media(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8").lower()

        self.assertIn('class="card__media fc-product-card__media--empty" aria-hidden="true"', card)
        self.assertRegex(
            css,
            re.compile(r"\.fc-collection-figma \.card__inner > \.card__content\s*\{[^}]*display:\s*none", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.fc-collection-figma \.card\.card--standard\.card--text:not\(\.card--horizontal\) > \.card__content \.card__heading:not\(\.card__heading--placeholder\)\s*\{[^}]*display:\s*block",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(r"\.fc-collection-figma \.card\.card--standard > \.card__content\s*\{[^}]*padding:\s*20px\s*!important", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(r"\.fc-collection-figma \.card__inner \.fc-product-card__media--empty\s*\{[^}]*display:\s*block", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(r"\.fc-collection-figma \.card__inner\s*\{[^}]*height:\s*23rem", re.DOTALL),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.fc-collection-figma \.card > \.card__content\s*\{[^}]*grid-template-rows:\s*minmax\(0,\s*7\.4rem\)\s+4rem[^}]*height:\s*17\.4rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(r"\.fc-collection-figma \.grid__item\s*\{[^}]*height:\s*40\.6rem", re.DOTALL),
        )

    def test_collection_card_long_titles_and_controls_share_refined_visual_contract(self) -> None:
        card = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8").lower()

        self.assertIn('title="{{ card_product.title | escape }}"', card)
        self.assertRegex(
            css,
            re.compile(
                r"\.fc-collection-figma \.card__heading \.full-unstyled-link\s*\{[^}]*-webkit-line-clamp:\s*2[^}]*overflow:\s*hidden",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"quantity-input-custom \.quantity__button:first-of-type\s*\{[^}]*border-right:\s*1px solid #ececed[^}]*margin-left:\s*0",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"quantity-input-custom \.quantity__button:last-of-type\s*\{[^}]*border-left:\s*1px solid #ececed[^}]*margin-right:\s*0",
                re.DOTALL,
            ),
        )
        self.assertIn(
            ".fc-collection-figma quantity-input-custom .submit_btn,\n.fc-collection-figma quick-add-bulk > .quick-add__submit",
            css,
        )
        for token in ("font-family: var(--font-body-family)", "font-size: 1.6rem", "font-weight: 500", "line-height: 1.25"):
            self.assertIn(token, css)

    def test_collection_card_reserves_two_line_title_slot_for_alignment(self) -> None:
        css = (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8").lower()

        self.assertRegex(
            css,
            re.compile(
                r"\.fc-collection-figma \.card__heading \.full-unstyled-link\s*\{[^}]*line-height:\s*1\.1[^}]*min-height:\s*2\.2em",
                re.DOTALL,
            ),
        )

    def test_card_quantity_handler_uses_bound_button_for_nested_icon_clicks(self) -> None:
        global_js = (ROOT / "assets" / "global.js").read_text(encoding="utf-8")
        custom_class = global_js.split("class QuantityInputCustom", 1)[1]
        handler = custom_class.split("onButtonClick(event) {", 1)[1].split("\n  }", 1)[0]

        self.assertIn("const button = event.currentTarget;", handler)
        self.assertIn("button.name === 'plus'", handler)
        self.assertNotIn("event.target.name", handler)
        self.assertNotIn("event.target.classList", handler)

    def test_quick_add_bulk_targets_custom_quantity_component(self) -> None:
        quick_add = (ROOT / "assets" / "quick-add-bulk.js").read_text(encoding="utf-8")

        self.assertIn("this.quantity = this.querySelector('quantity-input-custom');", quick_add)
        self.assertIn("return this.querySelector('quantity-input-custom input');", quick_add)

    def test_card_add_control_is_a_semantic_button(self) -> None:
        snippet = (ROOT / "snippets" / "quantity-input-custom.liquid").read_text(encoding="utf-8")
        global_js = (ROOT / "assets" / "global.js").read_text(encoding="utf-8")
        custom_quantity_js = global_js.split("class QuantityInputCustom", 1)[1].split(
            "customElements.define('quantity-input-custom'", 1
        )[0]
        self.assertRegex(
            snippet,
            re.compile(r'<button[^>]*type="button"[^>]*class="[^"]*\bsubmit_btn\b[^"]*"', re.DOTALL),
        )
        self.assertIn("</button>", snippet)
        self.assertIn("this.querySelectorAll('.quantity__button')", custom_quantity_js)
        self.assertNotIn("this.querySelectorAll('button').forEach", custom_quantity_js)

    def test_product_main_form_matches_figma_controls(self) -> None:
        buy_buttons = (ROOT / "snippets" / "buy-buttons.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "section-main-product.css").read_text(encoding="utf-8").lower()
        self.assertRegex(
            buy_buttons,
            re.compile(r"if main_product.*?render 'icon-cart-form'.*?products\.product\.add_to_cart", re.DOTALL),
        )
        self.assertIn(".product__info-container .price-per-item__container > .quantity", css)
        self.assertIn("width: 15.2rem", css)

    def test_product_form_controls_align_across_breakpoints(self) -> None:
        css = (ROOT / "assets" / "section-main-product.css").read_text(encoding="utf-8").lower()
        before_desktop_contract = css.split("/* product detail figma contract: 80846:313 */", 1)[0]
        selector = "product-info .product__info-container .price-per-item__container .product-form"
        self.assertIn(selector, before_desktop_contract)
        self.assertIn("min-height: 4.8rem", before_desktop_contract)

    def test_product_gallery_matches_figma_thumbnail_geometry(self) -> None:
        css = (ROOT / "assets" / "section-main-product.css").read_text(encoding="utf-8")

        self.assertRegex(
            css,
            re.compile(
                r"@media screen and \(min-width: 990px\).*?"
                r"product-info \.product--large:not\(\.product--no-media\) \.thumbnail-list\s*\{"
                r"[^}]*grid-template-columns:\s*repeat\(5,\s*minmax\(0,\s*1fr\)\)"
                r"[^}]*gap:\s*1\.6rem[^}]*padding:\s*0",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.product--large:not\(\.product--no-media\) \.thumbnail-slider\s*\{"
                r"[^}]*margin-top:\s*1\.6rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.product--large:not\(\.product--no-media\) \.thumbnail-list__item\.slider__slide\s*\{"
                r"[^}]*width:\s*auto[^}]*height:\s*10rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.product--large:not\(\.product--no-media\) \.thumbnail\s*\{"
                r"[^}]*border-radius:\s*1\.2rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.product--large:not\(\.product--no-media\) \.thumbnail\[aria-current\]\s*\{"
                r"[^}]*border:\s*0\.2rem solid #ea1a65[^}]*box-shadow:\s*none",
                re.DOTALL | re.IGNORECASE,
            ),
        )

    def test_product_price_row_uses_figma_label_and_native_shopify_price(self) -> None:
        liquid = (ROOT / "sections" / "main-product.liquid").read_text(encoding="utf-8")
        price_snippet = (ROOT / "snippets" / "price.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "section-main-product.css").read_text(encoding="utf-8")

        price_case = liquid.split("{%- when 'price' -%}", 1)[1].split("{%- when 'inventory' -%}", 1)[0]
        self.assertIn('class="fc-product-detail__price-row"', price_case)
        self.assertIn('class="fc-product-detail__price-label"', price_case)
        self.assertIn("Live Price:", price_case)
        self.assertRegex(
            price_case,
            re.compile(r"render 'price',\s*product:\s*product,\s*use_variant:\s*true", re.DOTALL),
        )
        self.assertIn("show_badges: false", price_case)
        self.assertNotIn("show_compare_at_price: false", price_case)
        self.assertIn('<s class="price-item price-item--regular">', price_snippet)
        self.assertNotRegex(price_case, re.compile(r"\$\s*\d"))
        self.assertRegex(
            css,
            re.compile(
                r"\.fc-product-detail__price-row\s*\{[^}]*display:\s*flex[^}]*gap:\s*2rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.fc-product-detail__price-row \.price_regular--label\s*\{"
                r"[^}]*display:\s*none\s*!important",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.fc-product-detail__price-row \.price__regular \.price-item,\s*"
                r"product-info \.fc-product-detail__price-row \.price__sale \.price-item--sale\s*\{"
                r"[^}]*color:\s*#ea1a65[^}]*font-weight:\s*600",
                re.DOTALL | re.IGNORECASE,
            ),
        )
        self.assertNotRegex(
            css,
            re.compile(r"product-info \.fc-product-detail__price-row \.price-item\s*\{"),
        )

    def test_product_purchase_row_fills_figma_width_with_native_quantity(self) -> None:
        liquid = (ROOT / "sections" / "main-product.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "section-main-product.css").read_text(encoding="utf-8")

        quantity_case = liquid.split("{%- when 'quantity_selector' -%}", 1)[1].split(
            "{%- when 'popup' -%}", 1
        )[0]
        self.assertIn("<quantity-input", quantity_case)
        self.assertIn("product.selected_or_first_available_variant.quantity_rule.min", quantity_case)
        self.assertIn("render 'buy-buttons'", quantity_case)
        self.assertNotRegex(quantity_case, re.compile(r'value=["\']06["\']'))

        self.assertRegex(
            css,
            re.compile(
                r"product-info \.product__info-container \.product-form__quantity\s*\{"
                r"[^}]*width:\s*100%[^}]*max-width:\s*none",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"product-info \.product__info-container \.price-per-item__container\s*\{"
                r"[^}]*width:\s*100%[^}]*gap:\s*2\.4rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"price-per-item__container > \.quantity\s*\{"
                r"[^}]*flex:\s*0 0 15\.2rem[^}]*width:\s*15\.2rem[^}]*height:\s*4\.8rem",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"price-per-item__container > \.product_form--container\s*\{"
                r"[^}]*flex:\s*1 1 0[^}]*min-width:\s*0",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"price-per-item__container \.product-form > \.form\s*\{"
                r"[^}]*width:\s*100%[^}]*max-width:\s*none",
                re.DOTALL,
            ),
        )

    def test_product_title_row_matches_figma_without_fake_wishlist_interaction(self) -> None:
        liquid = (ROOT / "sections" / "main-product.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "section-main-product.css").read_text(encoding="utf-8")

        title_case = liquid.split("{%- when 'title' -%}", 1)[1].split("{%- when 'price' -%}", 1)[0]
        self.assertIn('class="fc-product-detail__title-row"', title_case)
        self.assertIn("{{ product.title | escape }}", title_case)
        self.assertRegex(
            title_case,
            re.compile(
                r'<span[^>]*class="fc-product-detail__saved-marker"[^>]*aria-hidden="true"[^>]*>.*?render \'icon-heart-outline\'.*?</span>',
                re.DOTALL,
            ),
        )
        self.assertNotRegex(
            title_case,
            re.compile(r'<(?:button|a)[^>]*class="[^"]*fc-product-detail__saved-marker', re.IGNORECASE),
        )
        self.assertNotRegex(
            title_case,
            re.compile(r'<span[^>]*class="fc-product-detail__saved-marker"[^>]*tabindex=', re.IGNORECASE),
        )
        self.assertRegex(
            css,
            re.compile(
                r"\.fc-product-detail__saved-marker\s*\{[^}]*width:\s*2\.8rem[^}]*height:\s*2\.8rem[^}]*pointer-events:\s*none",
                re.DOTALL,
            ),
        )

    def test_product_detail_preserves_native_authorities(self) -> None:
        product = load_shopify_json(ROOT / "templates" / "product.json")
        blocks = product["sections"]["main"]["blocks"]
        related = product["sections"]["related-products"]["settings"]
        liquid = (ROOT / "sections" / "main-product.liquid").read_text(encoding="utf-8")
        form_js = (ROOT / "assets" / "product-form.js").read_text(encoding="utf-8")

        self.assertIn("inventory", blocks)
        self.assertIn("ripeness", blocks)
        self.assertEqual(related["columns_mobile"], "1")
        self.assertIn("selected_or_first_available_variant", liquid)
        self.assertIn("item_count_for_variant", liquid)
        self.assertIn("checkValidity()", form_js)
        self.assertIn("reportValidity()", form_js)

    def test_related_products_match_figma_geometry_and_shopify_authority(self) -> None:
        product = load_shopify_json(ROOT / "templates" / "product.json")
        settings = product["sections"]["related-products"]["settings"]
        liquid = (ROOT / "sections" / "related-products.liquid").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "section-related-products.css").read_text(encoding="utf-8")
        cards = (ROOT / "assets" / "freshclub-product-card.css").read_text(encoding="utf-8")

        self.assertEqual(settings["heading"], "Products You May Like")
        self.assertEqual(settings["products_to_show"], 8)
        self.assertEqual(settings["columns_desktop"], 4)
        self.assertEqual(settings["columns_mobile"], "1")
        self.assertEqual(settings["color_scheme"], "scheme-2")
        self.assertEqual(settings["padding_top"], 60)
        self.assertEqual(settings["padding_bottom"], 60)

        for authority in (
            "<product-recommendations",
            "routes.product_recommendations_url",
            "recommendations.performed and recommendations.products_count > 0",
            "recommendations.products",
            "render 'card-product'",
        ):
            self.assertIn(authority, liquid)

        for token in (
            "max-width: 144rem",
            "padding-inline: 8rem",
            "column-gap: 3.2rem",
            "row-gap: 3.2rem",
            "min-height: 40.6rem",
            "top: 3.9rem",
            "height: 17rem",
            "width: calc(100% - 4.8rem)",
        ):
            self.assertIn(token, css)

        self.assertRegex(
            css,
            re.compile(
                r"@media screen and \(min-width: 750px\).*?"
                r"--related-card-width:\s*calc\(\(100% - 3\.2rem\) / 2\)",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            css,
            re.compile(
                r"@media screen and \(min-width: 990px\).*?"
                r"\.related-products \.grid--4-col-desktop\s*\{[^}]*"
                r"--related-card-width:\s*calc\(\(100% - 9\.6rem\) / 4\)",
                re.DOTALL,
            ),
        )
        self.assertNotRegex(
            cards,
            re.compile(
                r"@media screen and \(min-width: 990px\)\s*\{\s*"
                r"\.related-products \.card__inner\s*\{[^}]*height:\s*28\.6rem",
                re.DOTALL,
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
