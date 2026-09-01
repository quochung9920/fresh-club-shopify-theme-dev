# Homepage Shopify Section Map

Authority:
- Desktop visual/content: Figma node `80795:364` (`v3`, 1440 × 4398).
- Mobile/tablet composition: verified FreshClub About Us and How Does It Work section patterns, per owner direction.
- Global shell: existing header, predictive search, cart, buttons, footer, newsletter, focus and hover systems.

## Ordered content sections

1. `fc-home-hero` — Homepage hero
   - One section owns heading, body, media and up to two independent action blocks.
   - Does not own header, search, cart or navigation.
2. `fc-home-benefits` — Why FreshClub
   - One repeatable `benefit` block per icon/title/text item.
   - Default template contains four blocks in Figma order.
3. `fc-home-story` — FreshClub difference
   - Section owns the shared heading.
   - Repeatable `story` blocks own image, alt, title, text, button label/link/style, desktop image side and packaged fallback asset.
   - Exact packaged Figma SVG connectors and gradient image panels are fixed decorative design assets, not merchant content settings.
   - Default template contains three blocks in right/left/right image order.
4. `fc-home-cta` — Homepage call to action
   - Section owns heading, subheading, text, background override and button.
   - Reuses global button behavior and packaged decorative assets.

Header and footer remain global section groups and must render exactly once.
