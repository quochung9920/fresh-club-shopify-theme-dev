# How It Works section map

Figma authority: desktop `81170:171` (1440px), mobile `81186:210` (375px).

1. `fc-how-hero` — eyebrow, H1, intro, two independent action blocks. No media.
2. `fc-how-steps` — section heading/intro plus reorderable `step` blocks. Each block owns number, title, body, image, alt text, desktop image side, and exact local fallback asset.
3. `fc-how-faq` — heading plus reorderable `faq` blocks. Each block owns question, answer and initial-open state. Native `details/summary` interaction.
4. `fc-how-cta` — editable CTA with exact How It Works 16px/24px radii; reuses the existing exact Figma background/decoration assets and global button authority without changing the passed About CTA.

Global header, footer, menu, predictive search, cart, newsletter, buttons, focus and motion remain owned by the theme and render once.