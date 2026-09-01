# Collection section map

Authority: Fresh Club | Website, Figma root `80841:1119` (`Collection`, 1440 × 2864).

## Global shell

The existing global header, predictive search, cart, newsletter, and footer remain the sole authorities. Collection code must not duplicate them.

## Collection-list policy

The Figma frame moves directly from the global header/search row to the product grid. The existing `collection_list` section remains available in Theme Editor but is disabled by default in `templates/collection.json`; it must not render in the Figma-default composition.

## Product grid

- Figma region: `80841:1228`, 1440 × 1442.
- Native owner: `sections/main-collection-product-grid.liquid`, `snippets/card-product.liquid`, and scoped collection CSS.
- Content owner: `collection.products`, selected/first available variants, native prices, unit pricing, inventory, and product URLs.
- Desktop target: 1280px inner container, four 296px cards, 32px column/row gaps, 12 products by default.
- Mobile requirement: exactly one product card per row below 750px.
- Tablet transition: two cards per row from 750–989px; this is derived behavior, not a Figma claim.
- Quick add must retain Dawn variant/inventory/sold-out machinery. Figma sample products and prices must never be hard-coded.

## FAQ

- Figma region: `80841:1246`, 1440 × 851.
- Native owner: `sections/collapsible-content.liquid` configured by `templates/collection.json`.
- Content owner: merchant-editable FAQ blocks.
- First row may be open by default; all rows must remain keyboard-operable native disclosure controls.

## Excluded until a real authority exists

The Figma heart is not rendered as a fake wishlist control. A real persisted wishlist requires a separately reviewed integration.
