# About Us — Mobile (node 81177:209)

Figma file: hW2EgKV2kCsp1pYLQHSdiR ("Fresh Club | Website")
Frame size: 375 x 4943 (mobile viewport)

## Design tokens used on this frame
- Brand/1 (dark teal/green): `#16494A`
- Brand/2 (pink/magenta, primary CTA): `#EA1A65`
- Brand/3 (pale mint background): `#F5FAF3`
- Base/Black: `#000000`
- Base/White: `#FFFFFF`
- Gray (light mode)/200: `#EAECF0`
- Gray (light mode)/300: `#D0D5DD`
- Gray (light mode)/400: `#98A2B3`
- Gray (light mode)/500: `#667085`
- Gray (light mode)/600: `#475467`
- Gray (light mode)/800: `#182230`
- Gray (light mode)/50: `#F9FAFB`
- Gray (dark mode)/200: `#ECECED`
- Gray (dark mode)/300: `#CECFD2`
- Gray (dark mode)/600: `#61646C`
- Foundation/Primary/primary-500: `#EA1A65`
- Shadows/shadow-xs: `drop-shadow(0px 1px 2px rgba(16,24,40,0.05))`

## Typography
- Font family: **Lexend Deca** (weights used: Regular, Medium, SemiBold, Bold)
- Secondary font seen on cart badge count: **DM Sans** (SemiBold)
- Google Fonts import needed: `Lexend+Deca` and `DM+Sans`

## Page structure (top to bottom, y-offset in px)
1. y=0 — Sticky header (promo/logo row + search row), border-bottom
2. y=176 — Hero: heading, subcopy, 2 CTA buttons ("Start Your Order" filled, "View Products" outline), hero image (rounded 16px)
3. y=978 — 4 "value" cards (Freshness You Can Trust / Honest, Transparent Pricing / Quality Over Quantity / Local & Accountable), white cards with icon badges, on `#F5FAF3` bg
4. y=1790 — Stats band, dark `#16494A` bg: "FRESHCLUB BY THE NUMBERS" + 2x2 stat grid (50 / 4AM / $0 / 100%)
5. y=2174 — "Built by people who know..." section: heading, framed photo, "It started with one question" text block + CTA button
6. y=2994 — "A day at FreshClub" section, `#F5FAF3` bg: heading + 4 numbered steps (TONIGHT / 4AM / 6AM / YOUR SLOT) each with dashed-border circular badge
7. y=4046 — CTA banner: dark overlay image bg, "Join The Club. Buy Fresher, For Less." + button
8. y=4522 — Footer: `#16494A` bg, logo, nav links (Home/Shop Product/About Us), newsletter signup (email input + Subscribe button), copyright, 4 social icons (LinkedIn/Instagram/Facebook/YouTube)

## Assets referenced (see ../81177-209/assets and ../81177-209/svg — downloaded separately)
See `asset-manifest.json` in this folder for the full name→URL→local-file mapping.

## Component notes from Figma
- **search-lg** icon (node 80730:18): tagged "search, search bar, searchbar, magnify, magnifying glass, filter"
- Buttons use a shared `Buttons/Button` component — rounded-[8px], padding 12px/24px (lg), primary = filled `#EA1A65` bg + white text; secondary = white/transparent bg + `#EA1A65` border/text

## Full reference code
See `design-context.jsx` — raw React+Tailwind reference pulled from Figma (node IDs kept as `data-node-id` attributes so you can cross-reference back to Figma). This is NOT meant to be used verbatim — treat it as a precise spec of layout, spacing, colors, and typography to translate into plain static HTML/CSS.
