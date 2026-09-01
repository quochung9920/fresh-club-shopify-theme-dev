#!/usr/bin/env python
"""Generate scoped Shopify CSS and install exact About Us runtime assets."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FEATURE = REPO / "prototype" / "about-us"
SOURCE = FEATURE / "reference" / "about-us_1.html"
WORKING_ASSETS = FEATURE / "working" / "assets"
THEME_ASSETS = REPO / "assets"
EXPECTED_SOURCE_SHA256 = "730247ac286a7123fcaea2459100e4905801557101aa9a25b433eddee7312329"

RUNTIME_FILES = (
    "freshclub-logo-header.png",
    "freshclub-value-freshness.png",
    "freshclub-value-pricing.png",
    "freshclub-value-quality.png",
    "freshclub-value-local.png",
    "freshclub-about-hero-base.jpg",
    "freshclub-about-hero-overlay.jpg",
    "freshclub-about-story.jpg",
    "freshclub-about-cta-bg.png",
    "freshclub-value-ring.png",
    "freshclub-about-cta-decoration.png",
    "freshclub-logo-footer.png",
    "lexend-deca-400.woff2",
    "lexend-deca-500.woff2",
    "lexend-deca-600.woff2",
    "lexend-deca-700.woff2",
    "dm-sans-600.woff2",
    "gsap-3.13.0.min.js",
)

REMOTE_TO_THEME = {
    "https://www.figma.com/api/mcp/asset/909084d5-4f69-4eaa-a9df-22d31a628f9d.png": "freshclub-about-hero-base.jpg",
    "https://www.figma.com/api/mcp/asset/b63097f3-4789-4b0e-b8f7-65e02b97fdc6.png": "freshclub-about-hero-overlay.jpg",
    "https://www.figma.com/api/mcp/asset/608d06e6-f679-427d-9888-6291f3e2473d.png": "freshclub-about-story.jpg",
    "https://www.figma.com/api/mcp/asset/429a790a-6898-4c86-890f-dd6f5b0db44a.png": "freshclub-about-cta-bg.png",
    "https://www.figma.com/api/mcp/asset/79318fa7-25a1-4d0c-a512-f09d97b6ea5c.png": "freshclub-value-ring.png",
}

FONT_CSS = """@font-face { font-family: 'Lexend Deca'; src: url('lexend-deca-400.woff2') format('woff2'); font-style: normal; font-weight: 400; font-display: swap; }
@font-face { font-family: 'Lexend Deca'; src: url('lexend-deca-500.woff2') format('woff2'); font-style: normal; font-weight: 500; font-display: swap; }
@font-face { font-family: 'Lexend Deca'; src: url('lexend-deca-600.woff2') format('woff2'); font-style: normal; font-weight: 600; font-display: swap; }
@font-face { font-family: 'Lexend Deca'; src: url('lexend-deca-700.woff2') format('woff2'); font-style: normal; font-weight: 700; font-display: swap; }
@font-face { font-family: 'DM Sans'; src: url('dm-sans-600.woff2') format('woff2'); font-style: normal; font-weight: 600; font-display: swap; }

freshclub-about-us[data-section-id] { display: block; width: 100%; }
"""

THEME_OVERRIDES = """
/* Override the baseline theme's explicit global heading color. */
freshclub-about-us[data-section-id] .fc-cta-title h2 { color: #fff; }
freshclub-about-us[data-section-id] .fc-newsletter h4 { color: #fff; }
/* Counter the baseline theme's generic `div:empty { display: none; }` rule. */
freshclub-about-us[data-section-id] .fc-photo-frame { display: block; }
freshclub-about-us[data-section-id] .fc-mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 20px 16px;
  background: #F5FAF3;
  border-bottom: 1px solid #EAECF0;
}
freshclub-about-us[data-section-id] .fc-mobile-nav[hidden] { display: none; }
freshclub-about-us[data-section-id] .fc-mobile-nav a {
  padding: 12px 16px;
  border-radius: 8px;
  color: #16494A;
  font-weight: 500;
}
freshclub-about-us[data-section-id] :is(a, button, input) {
  transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, box-shadow 160ms ease, filter 160ms ease;
}
freshclub-about-us[data-section-id] :is(a, button, input):focus-visible {
  outline: 3px solid #EA1A65;
  outline-offset: 3px;
}
freshclub-about-us[data-section-id] :is(.fc-search-field, .fc-newsletter-form):focus-within {
  border-color: #EA1A65;
  box-shadow: 0 0 0 3px rgba(234, 26, 101, 0.18);
}
freshclub-about-us[data-section-id] :is(.fc-btn, .fc-cart-btn, .fc-social a):active {
  filter: brightness(0.88);
}
@media (hover: hover) {
  freshclub-about-us[data-section-id] .fc-btn:hover { filter: brightness(0.92); }
  freshclub-about-us[data-section-id] :is(.fc-nav-desktop, .fc-footer-nav) a:hover { color: #EA1A65; }
  freshclub-about-us[data-section-id] .fc-cart-btn:hover { border-color: #EA1A65; }
  freshclub-about-us[data-section-id] .fc-social a:hover { background: #EA1A65; border-color: #EA1A65; }
}
@media (prefers-reduced-motion: reduce) {
  freshclub-about-us[data-section-id] *,
  freshclub-about-us[data-section-id] *::before,
  freshclub-about-us[data-section-id] *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
@media (min-width: 1024px) {
  freshclub-about-us[data-section-id] .fc-mobile-nav { display: none !important; }
  freshclub-about-us[data-section-id] .fc-header-spacer { display: block; }
  freshclub-about-us[data-section-id] .fc-story-panel { display: block; }
  freshclub-about-us[data-section-id] .fc-values-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 24px;
  }
}
"""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_exact_selector(css: str, selector: str, replacement: str) -> str:
    """Replace only a complete selector at a CSS rule boundary."""
    pattern = rf"(?m)^(\s*){re.escape(selector)}\s*\{{"
    return re.sub(pattern, rf"\1{replacement} {{", css)


def scope_selector_lines(css: str) -> str:
    """Scope every ordinary selector to the section custom element."""
    root = "freshclub-about-us[data-section-id]"
    zero_specificity_root = f":where({root})"
    output: list[str] = []
    for line in css.splitlines():
        stripped = line.lstrip()
        if "{" not in stripped or stripped.startswith(("@", "/*", "*")):
            output.append(line)
            continue
        indent = line[: len(line) - len(stripped)]
        selector_text, declarations = stripped.split("{", 1)
        scoped: list[str] = []
        for selector in selector_text.split(","):
            selector = selector.strip()
            if selector.startswith(".fc-about-root"):
                selector = zero_specificity_root + selector[len(".fc-about-root") :]
            elif selector.startswith(root):
                pass
            else:
                selector = f"{zero_specificity_root} {selector}"
            scoped.append(selector)
        output.append(f"{indent}{', '.join(scoped)} {{{declarations}")
    return "\n".join(output) + "\n"


def main() -> int:
    source_bytes = SOURCE.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != EXPECTED_SOURCE_SHA256:
        raise SystemExit("About Us HTML authority changed; refusing to regenerate theme assets")
    source = source_bytes.decode("utf-8")
    style_match = re.search(r"<style>(.*?)</style>", source, flags=re.S)
    body_match = re.search(r"<body>(.*?)</body>", source, flags=re.S)
    if not style_match or not body_match:
        raise SystemExit("Could not extract authoritative style/body blocks")

    css = style_match.group(1).strip() + "\n"
    body = body_match.group(1)
    classes = sorted(
        {
            token
            for value in re.findall(r'class="([^"]+)"', body)
            for token in value.split()
        },
        key=len,
        reverse=True,
    )

    for class_name in classes:
        css = re.sub(
            rf"\.{re.escape(class_name)}(?![A-Za-z0-9_-])",
            f".fc-{class_name}",
            css,
        )
    global_replacements = {
        ":root": ".fc-about-root",
        "*, *::before, *::after": ".fc-about-root *, .fc-about-root *::before, .fc-about-root *::after",
        "html": ".fc-about-root",
        "body": ".fc-about-root",
        "img, svg": ".fc-about-root img, .fc-about-root svg",
        "a": ".fc-about-root a",
        "button, input": ".fc-about-root button, .fc-about-root input",
        "button": ".fc-about-root button",
    }
    for old, new in global_replacements.items():
        css = replace_exact_selector(css, old, new)
    css = scope_selector_lines(css)
    for source_url, filename in REMOTE_TO_THEME.items():
        css = css.replace(source_url, filename)

    remaining_remote = sorted(set(re.findall(r"https?://[^)'\"]+", css)))
    unscoped_classes = sorted(
        class_name
        for class_name in classes
        if re.search(rf"\.{re.escape(class_name)}(?![A-Za-z0-9_-])", css)
    )
    if remaining_remote:
        raise SystemExit(f"Remote CSS dependencies remain: {remaining_remote}")
    if unscoped_classes:
        raise SystemExit(f"Unscoped CSS classes remain: {unscoped_classes}")

    css_output = THEME_ASSETS / "about-us-figma.css"
    css_output.write_text(FONT_CSS + css + THEME_OVERRIDES, encoding="utf-8", newline="\n")

    fixture = (FEATURE / "working" / "reference-local.html").read_text(encoding="utf-8")
    fixture = re.sub(r"<style(?:\s[^>]*)?>.*?</style>\s*", "", fixture, flags=re.S)
    fixture = fixture.replace(
        "</head>",
        '<style>html, body { margin: 0; } a:empty, ul:empty, dl:empty, div:empty, section:empty, article:empty, p:empty, h1:empty, h2:empty, h3:empty, h4:empty, h5:empty, h6:empty { display: none; } .fc-values-row { display: contents !important; }</style>\n'
        '<link rel="stylesheet" href="./assets/about-us-figma.css">\n</head>',
        1,
    )

    def prefix_fixture_classes(match: re.Match[str]) -> str:
        tokens = match.group(1).split()
        return 'class="' + " ".join(f"fc-{token}" for token in tokens) + '"'

    fixture = re.sub(r'class="([^"]+)"', prefix_fixture_classes, fixture)
    fixture = fixture.replace(
        '<button class="fc-menu-btn" type="button" aria-label="Open menu">',
        '<button class="fc-menu-btn" type="button" aria-label="Open menu" '
        'aria-expanded="false" aria-controls="AboutUsMenu-fixture">',
        1,
    )
    fixture = fixture.replace(
        '<div class="fc-header-row fc-header-row--search">',
        '<nav id="AboutUsMenu-fixture" class="fc-mobile-nav" aria-label="Mobile navigation" hidden>'
        '<a href="#about">About Us</a><a href="#products">View Products</a>'
        '<a href="#process">How does it work</a><a href="#contact">Contact Us</a></nav>\n'
        '<div class="fc-header-row fc-header-row--search">',
        1,
    )
    fixture = fixture.replace(
        "<body>",
        '<body><freshclub-about-us data-section-id="fixture" class="fc-about-root">',
        1,
    ).replace(
        "</body>",
        '</freshclub-about-us><script src="./assets/about-us-figma.js"></script></body>',
        1,
    )
    fixture_path = FEATURE / "working" / "liquid-css-fixture.html"
    fixture_path.write_text(fixture, encoding="utf-8", newline="\n")
    (FEATURE / "working" / "assets" / "about-us-figma.css").write_bytes(css_output.read_bytes())
    (FEATURE / "working" / "assets" / "about-us-figma.js").write_bytes(
        (THEME_ASSETS / "about-us-figma.js").read_bytes()
    )

    installed = []
    for filename in RUNTIME_FILES:
        source_path = WORKING_ASSETS / filename
        destination = THEME_ASSETS / filename
        if not source_path.is_file():
            raise SystemExit(f"Missing static runtime asset: {source_path}")
        destination.write_bytes(source_path.read_bytes())
        installed.append(
            {
                "file": destination.relative_to(REPO).as_posix(),
                "bytes": destination.stat().st_size,
                "sha256": digest(destination),
            }
        )
    installed.append(
        {
            "file": css_output.relative_to(REPO).as_posix(),
            "bytes": css_output.stat().st_size,
            "sha256": digest(css_output),
        }
    )
    authored_runtime = THEME_ASSETS / "about-us-figma.js"
    if not authored_runtime.is_file():
        raise SystemExit(f"Missing authored Shopify runtime: {authored_runtime}")
    installed.append(
        {
            "file": authored_runtime.relative_to(REPO).as_posix(),
            "bytes": authored_runtime.stat().st_size,
            "sha256": digest(authored_runtime),
        }
    )

    evidence = {
        "authority_sha256": EXPECTED_SOURCE_SHA256,
        "scoped_classes": len(classes),
        "remaining_remote_dependencies": remaining_remote,
        "unscoped_css_classes": unscoped_classes,
        "liquid_css_fixture": fixture_path.relative_to(REPO).as_posix(),
        "installed": installed,
    }
    evidence_path = FEATURE / "notes" / "theme-asset-build-verification.json"
    evidence_path.write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
