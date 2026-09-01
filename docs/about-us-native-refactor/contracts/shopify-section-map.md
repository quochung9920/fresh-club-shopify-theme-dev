# About Us Native Shopify Section Map

Status: FROZEN
Contract version: 1.0.0
Base commit: `55ce73b9cac5b17e940b511a7b14e2748ec6948c`

Evidence:

- `E:/Hermes-Secure-Data/fresh-club-shopify-ai-workspace/evidence/design-architecture/section-map.json`
- `E:/Hermes-Secure-Data/fresh-club-shopify-ai-workspace/evidence/design-architecture/responsive-pairing.json`
- `E:/Hermes-Secure-Data/fresh-club-shopify-ai-workspace/evidence/storefront-systems/homepage-system-inventory.json`

## Global shell authority

The About Us template uses the existing global `header-group` and `footer-group` exactly once. Page content must not render or configure navigation, predictive search, account/cart controls, newsletter, social links, footer menus, global buttons, or a second motion framework.

Restoring the global groups and removing the duplicated About shell are one atomic integration change. Doing only one half is invalid because it produces either a missing or duplicate shell.

## Template composition

| Order | Editor name | Type/file | Figma desktop/mobile | Responsibility | Repeated blocks |
|---:|---|---|---|---|---|
| 1 | About — Hero | `fc-about-hero` / `sections/fc-about-hero.liquid` | `81154:517` / `81177:317` | Intro copy, two independent actions, hero media | `button` (`Action`, 0–2) |
| 2 | About — Values | `fc-about-values` / `sections/fc-about-values.liquid` | `81154:425` / `81177:225` | Repeated value propositions | `value_card` (1–4) |
| 3 | About — Metrics | `fc-about-metrics` / `sections/fc-about-metrics.liquid` | `81154:409` / `81177:210` | Metrics eyebrow and proof points | `metric` (1–4) |
| 4 | About — Story | `fc-about-story` / `sections/fc-about-story.liquid` | `81154:535` / `81177:335` | Founding story, image, process action | none |
| 5 | About — Daily process | `fc-about-process` / `sections/fc-about-process.liquid` | `81154:552` / `81177:351` | Heading, introduction, ordered steps | `process_step` (1–4) |
| 6 | About — Call to action | `fc-about-cta` / `sections/fc-about-cta.liquid` | `81154:567` / `81177:376` | Closing conversion message and action | none |

## Merchant architecture rules

- Every section owns one semantic region and one editor card.
- Every section is independently selectable, addable, removable, hideable, and reorderable through the JSON template and presets.
- Every section owns a correspondingly named scoped stylesheet; parallel lanes never share a CSS file.
- Every repeated block renders `{{ block.shopify_attributes }}`.
- Repeated blocks use `heading` for meaningful dynamic editor titles.
- Value cards own their icon; the icon never derives from loop position.
- Decorative value icons use blank alt because the adjacent heading supplies the meaning.
- Hero actions each own their label, link, and closed `primary`/`secondary` style.
- Story and CTA actions are local section settings because each section contains one fixed action.
- Metrics map current explanatory text to `heading`; line wrapping is layout behavior, not merchant-authored newline control.
- Process badge typography derives from content; `large_badge` is removed.
- CTA background and side produce images are decorative and expose no misleading alt fields.
- Plain text and URLs are escaped contextually; intentional Shopify rich text remains markup.
- Unknown block types fail closed.
- Required content remains visible without JavaScript.

## Shared interaction authority

- Header/footer: existing Shopify section groups and settings.
- Search: existing global predictive-search implementation and ARIA/state contract.
- Buttons: existing `.button`, `.button--primary`, `.button--secondary`, focus, disabled, loading, and homepage hover behavior.
- Motion: existing theme reveal runtime; About-local GSAP is removed unless a separately approved interaction cannot use the shared system.
- Global shell breakpoint: 990px. Content breakpoints must not control shell topology.

## Required release checks

- Exactly six page sections in the required default order.
- Exactly one global header and one global footer.
- No About-local shell/search/cart/newsletter/social DOM remains.
- Query `apple` returns real predictive results on the authorized unpublished preview.
- Theme Editor add/remove/hide/reorder and block selection work.
- Button/search/menu/cart/newsletter/motion states match the homepage at 390, 768, and 1440.
- Exact-byte independent review and Git-native unpublished deployment gates pass.
