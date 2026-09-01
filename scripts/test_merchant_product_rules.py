from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_PRODUCT = ROOT / "sections" / "main-product.liquid"
PRODUCT_TEMPLATE = ROOT / "templates" / "product.json"
PRODUCT_INFO = ROOT / "assets" / "product-info.js"
PRODUCT_FORM = ROOT / "assets" / "product-form.js"
CART = ROOT / "assets" / "cart.js"
CART_FOOTER = ROOT / "sections" / "main-cart-footer.liquid"
CART_DRAWER = ROOT / "snippets" / "cart-drawer.liquid"
CART_CSS = ROOT / "assets" / "component-cart.css"
BASE_CSS = ROOT / "assets" / "base.css"
CART_NOTIFICATION = ROOT / "snippets" / "cart-notification.liquid"
CART_NOTIFICATION_JS = ROOT / "assets" / "cart-notification.js"
CART_RULES_GUARD = ROOT / "assets" / "cart-rules-guard.js"
CART_NOTIFICATION_RULES = ROOT / "sections" / "cart-notification-rules.liquid"
THEME_LAYOUT = ROOT / "layout" / "theme.liquid"
SETTINGS_DATA = ROOT / "config" / "settings_data.json"


def read_template() -> dict:
    source = PRODUCT_TEMPLATE.read_text(encoding="utf-8")
    source = re.sub(r"^/\*.*?\*/\s*", "", source, count=1, flags=re.S)
    return json.loads(source)


class MerchantProductRulesTest(unittest.TestCase):
    def test_ripeness_property_is_required_and_metafield_gated(self) -> None:
        liquid = MAIN_PRODUCT.read_text(encoding="utf-8")
        template = read_template()
        main = template["sections"]["main"]

        self.assertIn("'ripeness'", liquid)
        self.assertIn("product.metafields.custom.ripeness_options.value", liquid)
        self.assertIn('name="properties[Ripeness preference]"', liquid)
        self.assertRegex(liquid, r'name="properties\[Ripeness preference\]"[^>]*\brequired\b')
        self.assertIn('form="{{ product_form_id }}"', liquid)
        self.assertIn("{% if ripeness_options != blank %}", liquid)
        ripeness_case = liquid.split("{%- when 'ripeness' -%}", 1)[1].split("{%- when 'buy_buttons' -%}", 1)[0]
        self.assertNotRegex(ripeness_case, r"product\.(?:handle|title)")
        self.assertEqual(main["blocks"]["ripeness"]["type"], "ripeness")
        self.assertIn("ripeness", main["block_order"])
        self.assertLess(main["block_order"].index("variant_picker"), main["block_order"].index("ripeness"))
        self.assertLess(main["block_order"].index("ripeness"), main["block_order"].index("quantity_selector"))

        product_form = PRODUCT_FORM.read_text(encoding="utf-8")
        validity_gate = product_form.index("this.form.checkValidity()")
        form_data = product_form.index("new FormData(this.form)")
        fetch_cart = product_form.index("fetch(`${routes.cart_add_url}`")
        self.assertIn("this.form.reportValidity()", product_form)
        self.assertLess(validity_gate, form_data)
        self.assertLess(validity_gate, fetch_cart)

    def test_native_inventory_count_is_enabled_and_variant_refreshed(self) -> None:
        liquid = MAIN_PRODUCT.read_text(encoding="utf-8")
        template = read_template()
        product_info = PRODUCT_INFO.read_text(encoding="utf-8")
        main = template["sections"]["main"]
        inventory = main["blocks"]["inventory"]

        self.assertEqual(inventory["type"], "inventory")
        self.assertTrue(inventory["settings"]["show_inventory_quantity"])
        self.assertEqual(inventory["settings"]["inventory_threshold"], 100)
        self.assertIn("inventory", main["block_order"])
        self.assertLess(main["block_order"].index("price"), main["block_order"].index("inventory"))
        self.assertLess(main["block_order"].index("inventory"), main["block_order"].index("description"))
        self.assertIn("product.selected_or_first_available_variant.inventory_quantity", liquid)
        self.assertIn("product.selected_or_first_available_variant.inventory_policy == 'continue'", liquid)
        self.assertIn("1 box remaining", liquid)
        self.assertIn("boxes remaining", liquid)
        self.assertIn("updateSourceFromDestination('Inventory'", product_info)
        self.assertIn("toggleSubmitButton(", product_info)
        self.assertIn("window.variantStrings.soldOut", product_info)

    def test_avada_theme_embed_is_removed(self) -> None:
        settings_data = SETTINGS_DATA.read_text(encoding="utf-8")
        self.assertNotIn("avada-order-limits", settings_data.lower())

    def test_cart_notification_refreshes_rules_and_blocks_checkout(self) -> None:
        self.assertTrue(CART_NOTIFICATION_RULES.exists(), "notification rules section is required")
        notification = CART_NOTIFICATION.read_text(encoding="utf-8")
        notification_js = CART_NOTIFICATION_JS.read_text(encoding="utf-8")
        rules = CART_NOTIFICATION_RULES.read_text(encoding="utf-8")

        self.assertIn('id="cart-notification-rules"', notification)
        self.assertIn('id="cart-notification-checkout"', notification)
        self.assertIn("disabled", notification)
        self.assertIn('aria-describedby="cart-notification-rules"', notification)
        self.assertIn("id: 'cart-notification-rules'", notification_js)
        self.assertIn("updateCheckoutState()", notification_js)
        self.assertIn("disableCheckout()", notification_js)
        self.assertIn("parsedState.sections?.[section.id]", notification_js)
        self.assertIn("sectionElement.innerHTML = ''", notification_js)
        self.assertIn("querySelector(selector)?.innerHTML ?? ''", notification_js)
        self.assertIn("data-cart-rules-valid", notification_js)
        for token in (
            "assign minimum_order_cents = 50000",
            "assign maximum_product_quantity = 10",
            "cart.items_subtotal_price",
            "candidate_item.product.id == product_item.product.id",
            "product_quantity_total > maximum_product_quantity",
            "minimum_order_cents | minus: cart.items_subtotal_price",
            "data-cart-rules-valid",
            "Add {{ minimum_order_remaining | money }} more to reach the $500 minimum.",
            "Maximum 10 units per product",
        ):
            self.assertIn(token, rules)

    def test_app_mutation_guard_is_loaded_and_owns_invalid_state(self) -> None:
        self.assertTrue(CART_RULES_GUARD.exists())
        layout = THEME_LAYOUT.read_text(encoding="utf-8")
        notification = CART_NOTIFICATION.read_text(encoding="utf-8")
        footer = CART_FOOTER.read_text(encoding="utf-8")
        drawer = CART_DRAWER.read_text(encoding="utf-8")
        notification_js = CART_NOTIFICATION_JS.read_text(encoding="utf-8")
        guard = CART_RULES_GUARD.read_text(encoding="utf-8")

        self.assertIn("{{ 'cart-rules-guard.js' | asset_url }}", layout)
        for source in (notification, footer, drawer):
            self.assertIn('data-cart-rules-disabled="true"', source)
        self.assertIn("window.FreshClubCartRulesGuard.sync(checkoutButton)", notification_js)
        self.assertIn("MutationObserver", guard)
        self.assertIn("stopImmediatePropagation", guard)
        self.assertIn("dingdoong-disabled-checkout", guard)

    def test_cart_ux_enforces_product_ten_and_order_minimum_five_hundred(self) -> None:
        footer = CART_FOOTER.read_text(encoding="utf-8")
        drawer = CART_DRAWER.read_text(encoding="utf-8")
        cart_js = CART.read_text(encoding="utf-8")
        base_css = BASE_CSS.read_text(encoding="utf-8")

        for source in (footer, drawer):
            self.assertIn("assign minimum_order_cents = 50000", source)
            self.assertIn("assign maximum_product_quantity = 10", source)
            self.assertIn("cart.items_subtotal_price", source)
            self.assertIn("for product_item in cart.items", source)
            self.assertIn("for candidate_item in cart.items", source)
            self.assertIn("candidate_item.product.id == product_item.product.id", source)
            self.assertIn("product_quantity_total | plus: candidate_item.quantity", source)
            self.assertIn("product_quantity_total > maximum_product_quantity", source)
            self.assertIn("minimum_order_cents | minus: cart.items_subtotal_price", source)
            self.assertIn("Add {{ minimum_order_remaining | money }} more to reach the $500 minimum.", source)
            self.assertIn("Maximum 10 units per product", source)
            self.assertIn("unless cart_rules_valid", source)
            self.assertIn("disabled", source)
            self.assertIn('aria-describedby="CartRules-', source)
            self.assertIn("cart__business-rules--valid", source)
            self.assertIn("cart__business-rules--invalid", source)
            self.assertIn('data-cart-rules-valid="{{ cart_rules_valid }}"', source)

        self.assertIn(".cart__business-rules {", base_css)
        self.assertIn(".cart__business-rules--valid", base_css)
        self.assertIn(".cart__business-rules--invalid", base_css)
        self.assertNotRegex(base_css, r"(?s)\.cart__business-rules[^}]*overflow\s*:\s*(?:hidden|clip)")

        self.assertIn("{% unless cart_rules_valid %}hidden{% endunless %}", footer)
        self.assertRegex(
            cart_js,
            r"(?s)id:\s*'main-cart-footer'.*?selector:\s*'#main-cart-footer'",
        )


if __name__ == "__main__":
    unittest.main()
