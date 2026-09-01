# About Us — Desktop (node 81154:408)

Figma file: hW2EgKV2kCsp1pYLQHSdiR ("Fresh Club | Website")
Frame size: 1440 x 4191 (desktop viewport)

This is the desktop version of the same page as `81177-209` (mobile). Same
sections, same copy, same color/typography tokens — only the layout, spacing,
and font sizes scale up. See that folder's `notes.md` for the shared design
token table; differences below are desktop-specific.

## Desktop-specific layout notes
- Container padding: 80px horizontal (vs 20px on mobile)
- Header nav is a single 2-row bar (top: logo + nav links + cart button;
  bottom: full-width search bar + "Contact Us" button), each row h=100px,
  total header h=200px, sticky/border-bottom `#EAECF0`
- Nav links (top row): About Us, View Products, How does it work
- Footer nav links: Home, Shop Product, About Us
- Hero heading: 48px, hero paragraph: 18px/760px max-width, 2 CTAs side by side
- Hero image: 1280px wide x 360px tall, rounded-24px
- Value cards (Freshness/Pricing/Quality/Local): 2x2 grid, each card 628px
  wide, 28px padding, icon badge 100px
- Stats band: single row of 4 stats (50 / 4AM / $0 / 100%), number size 56px
- "Built by people..." section: heading 44px, two-column layout (text block
  648px + photo 470px), decorative gradient blob behind photo
  (`linear-gradient(229.25deg, #34AEB0 12.7%, #FFFFFF 78.013%)`), plus a
  decorative wavy ellipse SVG background (`imgEllipse6`)
  and two rotated "Hero-img" decorative photo strips flanking the CTA banner
  lower down (see `imgHreoImg`, rotated 90°, one mirrored)
- "A day at FreshClub" steps: single row of 4, each 296px wide
- CTA banner: rounded-24px, 48px padding, heading 32px, decorative rotated
  photo strips left/right (desktop only — not present on mobile)
- Footer: nav links + logo on left, newsletter signup on right (justify-between),
  single row footer bottom (copyright + social icons) instead of stacked

## Assets referenced (see ../81154-408/assets and ../81154-408/svg)
See `asset-manifest.json` in this folder for the full name→URL→local-file mapping.
Note: desktop frame has 2 extra unique assets vs mobile — `imgEllipse6` (wavy
background SVG behind "Built by people" section) and `imgHreoImg` (rotated
decorative photo strip used twice in the CTA banner).

## Full reference code
See `design-context.jsx` — raw React+Tailwind reference pulled from Figma
(node IDs kept as `data-node-id` attributes). Treat as a precise spec of
layout/spacing/color/typography to translate into plain static HTML/CSS —
not to be used verbatim.
