import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StockConfirmationContractTests(unittest.TestCase):
    def test_buy_buttons_expose_managed_inventory_and_confirmation(self) -> None:
        liquid = (ROOT / "snippets" / "buy-buttons.liquid").read_text(encoding="utf-8")

        self.assertIn("assign stock_confirmation_enabled = false", liquid)
        self.assertIn("inventory_management == 'shopify'", liquid)
        self.assertIn("inventory_policy != 'continue'", liquid)
        self.assertIn('data-stock-limit="{{ product.selected_or_first_available_variant.inventory_quantity }}"', liquid)
        self.assertIn("cart | item_count_for_variant: product.selected_or_first_available_variant.id", liquid)
        self.assertIn('data-stock-cart-quantity="{{ stock_cart_quantity }}"', liquid)
        self.assertIn("data-stock-product-url=", liquid)
        self.assertIn("data-stock-refresh-url=", liquid)
        self.assertIn("data-stock-form-key=", liquid)
        self.assertIn("data-stock-variant-id=", liquid)
        self.assertIn("data-stock-min=", liquid)
        self.assertIn("data-stock-increment=", liquid)
        self.assertIn("assign maximum_product_quantity = 10", liquid)
        self.assertIn("candidate_item.product.id == product.id", liquid)
        self.assertIn("data-product-cart-quantity=", liquid)
        self.assertIn("data-product-quantity-limit=", liquid)
        self.assertIn("append: block.id", liquid)
        self.assertIn("render 'stock-confirmation'", liquid)

    def test_card_product_forms_share_stock_confirmation_contract(self) -> None:
        liquid = (ROOT / "snippets" / "card-product.liquid").read_text(encoding="utf-8")
        ripeness_branch = liquid.split("{% if has_ripeness_quick_add %}", 1)[1].split(
            "{% elsif quick_add == 'standard' %}", 1
        )[0]
        direct_branch = liquid.split("{% elsif quick_add == 'standard' %}", 1)[1].split(
            "{% elsif quick_add == 'bulk' %}", 1
        )[0]

        self.assertIn("inventory_management == 'shopify'", liquid)
        self.assertIn("inventory_policy != 'continue'", liquid)
        self.assertIn("assign maximum_product_quantity = 10", liquid)
        self.assertIn("candidate_item.product.id == card_product.id", liquid)
        for branch in (ripeness_branch, direct_branch):
            self.assertIn("data-stock-limit=", branch)
            self.assertIn("data-stock-cart-quantity=", branch)
            self.assertIn("data-stock-product-url=", branch)
            self.assertIn("data-stock-refresh-url=", branch)
            self.assertIn("data-stock-refresh-query", branch)
            self.assertIn("data-stock-form-key=", branch)
            self.assertIn("data-stock-variant-id=", branch)
            self.assertIn("data-stock-min=", branch)
            self.assertIn("data-stock-increment=", branch)
            self.assertIn("data-product-cart-quantity=", branch)
            self.assertIn("data-product-quantity-limit=", branch)
            self.assertIn("render 'stock-confirmation'", branch)

    def test_stock_confirmation_markup_is_accessible_and_scoped(self) -> None:
        liquid = (ROOT / "snippets" / "stock-confirmation.liquid").read_text(encoding="utf-8")

        self.assertIn("<dialog", liquid)
        self.assertIn("data-stock-confirmation", liquid)
        self.assertIn('aria-labelledby="StockConfirmationTitle-{{ confirmation_id }}"', liquid)
        self.assertIn('aria-describedby="StockConfirmationMessage-{{ confirmation_id }}"', liquid)
        self.assertIn("data-stock-confirmation-requested", liquid)
        self.assertIn("data-stock-confirmation-remaining", liquid)
        self.assertIn("Available now", liquid)
        self.assertIn('type="number"', liquid)
        self.assertIn("data-stock-confirmation-quantity", liquid)
        self.assertIn("data-stock-confirmation-cancel", liquid)
        self.assertIn("data-stock-confirmation-confirm", liquid)

    def test_variant_and_cart_refresh_sync_stock_metadata(self) -> None:
        product_info = (ROOT / "assets" / "product-info.js").read_text(encoding="utf-8")

        self.assertEqual(product_info.count("this.updateProductFormInventory(html)"), 1)
        method = product_info.split("updateProductFormInventory(html) {", 1)[1].split("get productForm()", 1)[0]
        self.assertIn("const sourceProductForm", method)
        self.assertIn("data-stock-form-key", method)
        self.assertNotIn("html.querySelector('product-form')", method)
        self.assertIn("this.productForm?.updateInventoryFrom(sourceProductForm)", method)

    def test_product_form_refreshes_authority_and_honors_quantity_rules(self) -> None:
        product_form = (ROOT / "assets" / "product-form.js").read_text(encoding="utf-8")

        self.assertIn("async refreshInventoryFromServer", product_form)
        self.assertIn("getAddableStock", product_form)
        self.assertIn("stockMin", product_form)
        self.assertIn("stockIncrement", product_form)
        self.assertIn("this.form.elements.namedItem('quantity')", product_form)
        self.assertIn("this.stockConfirmationQuantity.checkValidity()", product_form)
        self.assertIn("getMinimumAddableStock", product_form)
        self.assertIn("productQuantityLimit", product_form)
        self.assertIn("productCartQuantity", product_form)
        self.assertIn("recoverFromStockError", product_form)
        self.assertIn("this.stockRecoveryCount >= 1", product_form)

    def test_nested_dialog_escape_is_isolated(self) -> None:
        product_form = (ROOT / "assets" / "product-form.js").read_text(encoding="utf-8")

        self.assertIn("this.onStockConfirmationEscape", product_form)
        self.assertIn("this.stockConfirmation?.addEventListener('cancel'", product_form)
        self.assertIn("event.stopPropagation()", product_form)

    def test_stock_confirmation_is_polished_and_responsive(self) -> None:
        css = (ROOT / "assets" / "base.css").read_text(encoding="utf-8")

        self.assertIn(".stock-confirmation::backdrop", css)
        self.assertIn(".stock-confirmation__content", css)
        self.assertIn("max-width: 48rem", css)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("min-height: 4.4rem", css)
        self.assertIn(".stock-confirmation__quantity-input", css)
        self.assertIn(".stock-confirmation [hidden]", css)
        self.assertIn("translateY(-0.2rem)", css)
        self.assertRegex(css, re.compile(r"@media screen and \(max-width: 749px\).*?\.stock-confirmation__actions", re.DOTALL))
        self.assertRegex(css, re.compile(r"@media \(prefers-reduced-motion: reduce\).*?\.stock-confirmation", re.DOTALL))


if __name__ == "__main__":
    unittest.main(verbosity=2)
