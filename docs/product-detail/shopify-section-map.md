# Product Detail section map

Authority: Fresh Club | Website, Figma root `80846:250` (`Product Detail`, 1440 × 2596).

## Shared global shell

The existing theme header, predictive search, cart affordance, newsletter, and footer remain the sole authorities. Product-page code must not duplicate or replace them.

## Main product

- Figma child: `80846:313` (1440 × 834).
- Native Shopify owner: `sections/main-product.liquid` + `assets/section-main-product.css`.
- Content owner: Shopify `product` and selected variant.
- Desktop inner geometry: 1280px max width, 80px horizontal gutters, 60px column gap, 575px media column, 645px info column.
- Gallery: one native primary media surface with native thumbnail controls. Exact rendered media comes from `product.media`; no Figma sample raster is hard-coded.
- Information: semantic H1, selected-variant price, merchant product description, native quantity input, native Add to Cart form.
- The pale curved transition is a required shared Fresh Club section separator and must not alter reading order.
- Curve markup owner: `sections/main-product.liquid` (`curve-line-container` → `curve-line`). Curve geometry owner: the shared `.curved-section` rules in `assets/base.css`, matching the Homepage visual language across mobile, tablet, and desktop.

### Shopify Admin ownership

| Figma/storefront element | Shopify authority | Merchant edit location |
| --- | --- | --- |
| Product title | `product.title` | Products → select product → Title |
| Main image and gallery | ordered `product.media` | Products → select product → Media |
| Price and sale price | selected variant `price` / `compare_at_price` | Products → select product → Pricing or Variants |
| “Live Price” and “Per Kg” | selected variant `unit_price` + `unit_price_measurement` | Products → select variant → unit pricing/measurement |
| “About The Product” copy | `product.description` | Products → select product → Description |
| Description label | Main Product description block setting | Online Store → Themes → Customize → Products → Default product |
| Variant choices | native product options/variants | Products → select product → Options and Variants |
| Availability/Sold out | selected variant inventory and availability | Products → select variant → Inventory |
| Quantity and Add to Cart | native product form for selected variant | Theme behavior; inventory/variant data remains under Products |

The theme does not invent a unit label. If a product must show “Per Kg”, its variant must have Shopify unit-price measurement configured. Product media should be supplied at a resolution suitable for the 575 × 558px desktop stage; the current Alfalfa Sprouts source is only 260 × 145px and therefore upscales visibly.

## Products You May Like

- Figma child: `80846:251` (1440 × 1191).
- Native Shopify owner: `sections/related-products.liquid` + `assets/section-related-products.css`.
- Data owner: Shopify Product Recommendations API.
- Desktop: 4 columns, 8 products, 296 × 406px nominal/minimum target cards, 32px horizontal and vertical gaps within a 1280px container. Cards grow rather than clip merchant-variable content or native quick-add states.
- Mobile: exactly 1 product card per row for every viewport below 750px.
- Empty recommendations remain honestly empty; sample Figma products are never hard-coded.

### Related products Admin ownership

| Storefront element | Shopify authority | Merchant edit location |
| --- | --- | --- |
| Section heading | `related-products` section setting | Theme Customize → Products → Default product → Product recommendations |
| Recommended products | Shopify Product Recommendations API | Shopify Search & Discovery recommendations, when installed; otherwise Shopify automatic recommendations |
| Product image/title/price/availability | each recommended Shopify product/variant | Products → select the recommended product |
| Number of products, desktop columns, image ratio, quick add | section settings | Theme Customize → Product recommendations |
| Mobile columns | section setting, default `1` | Theme Customize → Product recommendations; this template is pinned to `1` |

Tablet uses two columns from 750–989px as a derived transition; desktop returns to the four-column Figma composition at 990px and above.

## Excluded until an authority exists

Figma heart icons are not rendered as fake wishlist controls. A future real wishlist integration may add them through a separate reviewed contract.
