from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
RUNTIME_ROOTS = ("assets", "config", "layout", "locales", "sections", "snippets", "templates")


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def text(path: str) -> str:
    file_path = ROOT / path
    require(file_path.is_file(), f"missing {path}")
    return file_path.read_text(encoding="utf-8") if file_path.is_file() else ""


def file_sha256(path: str) -> str:
    file_path = ROOT / path
    require(file_path.is_file(), f"missing {path}")
    return hashlib.sha256(file_path.read_bytes()).hexdigest() if file_path.is_file() else ""


def runtime_tree_sha256() -> tuple[int, str]:
    invalid_entries: list[str] = []
    digest = hashlib.sha256()
    count = 0

    def signature(metadata: os.stat_result) -> tuple[int, ...]:
        return (
            metadata.st_dev,
            metadata.st_ino,
            stat.S_IFMT(metadata.st_mode),
            metadata.st_nlink,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )

    def consume(relative: str, contents: bytes) -> None:
        nonlocal count
        count += 1
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(contents).digest())

    if os.name != "nt" and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        file_flags = os.O_RDONLY | os.O_NOFOLLOW

        def walk_directory(directory_fd: int, prefix: str) -> None:
            start_metadata = os.fstat(directory_fd)
            names = sorted(entry.name for entry in os.scandir(directory_fd))
            for name in names:
                relative = f"{prefix}/{name}"
                try:
                    path_metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError as exc:
                    invalid_entries.append(f"{relative} (cannot lstat: {exc})")
                    continue
                if stat.S_ISLNK(path_metadata.st_mode):
                    invalid_entries.append(f"{relative} (symbolic link)")
                elif stat.S_ISDIR(path_metadata.st_mode):
                    try:
                        child_fd = os.open(name, directory_flags, dir_fd=directory_fd)
                    except OSError as exc:
                        invalid_entries.append(f"{relative} (cannot open directory without following links: {exc})")
                        continue
                    try:
                        opened_metadata = os.fstat(child_fd)
                        if (opened_metadata.st_dev, opened_metadata.st_ino) != (path_metadata.st_dev, path_metadata.st_ino):
                            invalid_entries.append(f"{relative} (directory identity changed before open)")
                        walk_directory(child_fd, relative)
                        rebound_metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                        if signature(rebound_metadata) != signature(os.fstat(child_fd)):
                            invalid_entries.append(f"{relative} (directory path binding changed during scan)")
                    finally:
                        os.close(child_fd)
                elif stat.S_ISREG(path_metadata.st_mode):
                    try:
                        file_fd = os.open(name, file_flags, dir_fd=directory_fd)
                    except OSError as exc:
                        invalid_entries.append(f"{relative} (cannot open file without following links: {exc})")
                        continue
                    with os.fdopen(file_fd, "rb") as handle:
                        opened_metadata = os.fstat(handle.fileno())
                        if (opened_metadata.st_dev, opened_metadata.st_ino) != (path_metadata.st_dev, path_metadata.st_ino):
                            invalid_entries.append(f"{relative} (file identity changed before open)")
                        if not stat.S_ISREG(opened_metadata.st_mode):
                            invalid_entries.append(f"{relative} (not a regular file)")
                        if opened_metadata.st_nlink != 1:
                            invalid_entries.append(f"{relative} (hard-linked runtime file)")
                        contents = handle.read()
                        readback_metadata = os.fstat(handle.fileno())
                    if signature(readback_metadata) != signature(opened_metadata):
                        invalid_entries.append(f"{relative} (file changed while being read)")
                    rebound_metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if signature(rebound_metadata) != signature(readback_metadata):
                        invalid_entries.append(f"{relative} (file path binding changed during scan)")
                    consume(relative, contents)
                else:
                    invalid_entries.append(f"{relative} (non-regular entry)")
            if names != sorted(entry.name for entry in os.scandir(directory_fd)):
                invalid_entries.append(f"{prefix} (directory inventory changed during scan)")
            if signature(os.fstat(directory_fd)) != signature(start_metadata):
                invalid_entries.append(f"{prefix} (directory metadata changed during scan)")

        root_fd = os.open(ROOT, directory_flags)
        try:
            root_metadata = os.fstat(root_fd)
            for root_name in RUNTIME_ROOTS:
                try:
                    runtime_root_fd = os.open(root_name, directory_flags, dir_fd=root_fd)
                except OSError as exc:
                    invalid_entries.append(f"{root_name} (cannot open real runtime root: {exc})")
                    continue
                try:
                    walk_directory(runtime_root_fd, root_name)
                    rebound_root = os.stat(root_name, dir_fd=root_fd, follow_symlinks=False)
                    if signature(rebound_root) != signature(os.fstat(runtime_root_fd)):
                        invalid_entries.append(f"{root_name} (runtime root path binding changed during scan)")
                finally:
                    os.close(runtime_root_fd)
            live_root = os.stat(ROOT, follow_symlinks=False)
            if signature(live_root) != signature(root_metadata):
                invalid_entries.append("repository root path binding changed during scan")
        finally:
            os.close(root_fd)
    else:
        files: list[Path] = []

        def inventory(directory: Path) -> None:
            with os.scandir(directory) as entries:
                for entry in entries:
                    entry_path = Path(entry.path)
                    relative = entry_path.relative_to(ROOT).as_posix()
                    if entry.is_symlink():
                        invalid_entries.append(f"{relative} (symbolic link)")
                    elif entry.is_dir(follow_symlinks=False):
                        inventory(entry_path)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry_path)
                    else:
                        invalid_entries.append(f"{relative} (non-regular entry)")

        for root_name in RUNTIME_ROOTS:
            root_path = ROOT / root_name
            if root_path.is_symlink() or not root_path.is_dir():
                invalid_entries.append(f"{root_name} (missing, symbolic-link, or non-directory root)")
            else:
                inventory(root_path)
        for file_path in sorted(files, key=lambda path: path.relative_to(ROOT).as_posix()):
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
            try:
                descriptor = os.open(file_path, flags)
            except OSError as exc:
                invalid_entries.append(f"{file_path.relative_to(ROOT).as_posix()} (cannot open: {exc})")
                continue
            with os.fdopen(descriptor, "rb") as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    invalid_entries.append(f"{file_path.relative_to(ROOT).as_posix()} (not a single-link regular file)")
                contents = handle.read()
            consume(file_path.relative_to(ROOT).as_posix(), contents)

    require(not invalid_entries, "Shopify runtime tree topology or bytes changed: " + ", ".join(invalid_entries))
    return count, digest.hexdigest()


def parse_shopify_json(source: str, path: str) -> dict:
    try:
        return json.loads(re.sub(r"^/\*.*?\*/\s*", "", source, flags=re.S))
    except json.JSONDecodeError as exc:
        require(False, f"invalid JSON in {path}: {exc}")
        return {}


def liquid_schema(source: str, path: str) -> dict:
    match = re.search(r"{% schema %}\s*(\{.*?\})\s*{% endschema %}", source, re.S)
    require(match is not None, f"missing schema in {path}")
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        require(False, f"invalid schema in {path}: {exc}")
        return {}


contract_paths = [
    "docs/product-detail/shopify-section-map.md",
    "docs/product-detail/editor-schema-contract.json",
    "docs/product-detail/interaction-contract.json",
    "docs/product-detail/responsive-contract.json",
    "docs/product-detail/content-migration-contract.json",
    "docs/product-detail/file-ownership.json",
]
for contract_path in contract_paths:
    text(contract_path)

responsive_contract = parse_shopify_json(text("docs/product-detail/responsive-contract.json"), "docs/product-detail/responsive-contract.json")
editor_contract = parse_shopify_json(text("docs/product-detail/editor-schema-contract.json"), "docs/product-detail/editor-schema-contract.json")
require(responsive_contract.get("breakpoints", {}).get("tablet", {}).get("relatedProductsColumns") == 2, "responsive contract must require two recommendation columns on tablet")
require(responsive_contract.get("breakpoints", {}).get("tablet", {}).get("cssRange") == "min-width: 750px; desktop override begins at 990px", "responsive contract must describe a gap-free tablet-default/desktop-override cascade")
require(
    {"duplicate global header", "duplicate global footer", "fake wishlist button"}.issubset(set(editor_contract.get("forbidden", []))),
    "editor contract must explicitly forbid duplicate shell and fake wishlist ownership",
)

main_path = "sections/main-product.liquid"
related_path = "sections/related-products.liquid"
template_path = "templates/product.json"
main = text(main_path)
related = text(related_path)
main_css = text("assets/section-main-product.css")
related_css = text("assets/section-related-products.css")
base_css = text("assets/base.css")
template = parse_shopify_json(text(template_path), template_path)
related_schema = liquid_schema(related, related_path)

# These seven files are the reviewed Product Detail rendering authorities. Exact
# byte pins deliberately make the gate fail closed across template composition,
# the global stylesheet loader/cascade, and section-local rendering: semantic
# alternatives such as encoded controls, selector aliases, formatting tricks,
# inline sample cards, or competing CSS cannot bypass a finite token blacklist.
# Any intentional authority change must update its pin and receive a fresh exact-diff review.
reviewed_authority_sha256 = {
    "sections/main-product.liquid": "cdc2c669f9272a7c4d4e850df3b4c934d53a88822c06175c81cd6923498b0263",
    "sections/related-products.liquid": "525c872a7340df043b07fa35c839c49c848e99e1e56bfaa4fe8ed6ff5f57691a",
    "assets/section-main-product.css": "23c2a26353d4465c4a9ab074b612949b2976df11765427fa783ee6eb0abe1135",
    "assets/section-related-products.css": "71caf505452a34ada640001b8174b52f45d363f3b7f90cc04a2bed3b76b44a69",
    "assets/freshclub-product-card.css": "5ded21d42e5f316a453f5e9785561531988b1c85c738fd63e80afdaf65977b5b",
    "assets/global.js": "9bfbd40fd1a4003168c93d6e5d84937e586962bdf6a430cc2607bf4051b8b645",
    "snippets/buy-buttons.liquid": "f81dc9e38caf0d14a37797505f5136fb4b87d315cebb30fc93a08d6bdcc32178",
    "snippets/quantity-input-custom.liquid": "f642fd355909ee8e5fb12143d1dac41338ba0b1273dfc3d8b442642e605a4830",
    "assets/base.css": "6d25a50a3f4f994c95c178c79b08fb0f697b43a34d5e403a735a0e9797ea171a",
    "templates/product.json": "ec3903ae36be05ba9c1e5828468b13b59cbc6ad664307ca632284b94ad51e9d1",
    "layout/theme.liquid": "5c6bac606d760de39dc5723df0547893276dd4879f9d20c198184a5b80a1fa5d",
}
for authority_path, expected_sha256 in reviewed_authority_sha256.items():
    require(
        file_sha256(authority_path) == expected_sha256,
        f"reviewed Product Detail authority bytes changed: {authority_path}",
    )

runtime_file_count, runtime_digest = runtime_tree_sha256()
require(runtime_file_count == 437, "Shopify runtime tree file inventory changed")
require(
    runtime_digest == "f66af7eaacfab132531b5ba6dff5177360efc98b3a3300f0fecea040a027acb9",
    "Shopify runtime tree bytes/path inventory changed; refresh authority only through exact review",
)

sections = template.get("sections", {})
main_template = sections.get("main", {})
related_template = sections.get("related-products", {})
related_settings = related_template.get("settings", {})

require(main_template.get("type") == "main-product", "product template must keep native main-product section")
require(main_template.get("settings", {}).get("padding_top") == 80, "main product desktop top padding must match Figma 80px")
require(main_template.get("settings", {}).get("padding_bottom") == 80, "main product desktop bottom padding must match Figma 80px")
require(related_template.get("type") == "related-products", "product template must keep native related-products section")
require(template.get("order") == ["main", "related-products"], "product template section order")
require("{% render 'product-media-gallery'" in main, "main product must keep native media gallery")
require("{{ product.title | escape }}" in main, "main product title must come from Shopify product data")
require("{{ product.description }}" in main, "main product description must come from Shopify product data")
require(re.search(r"{%[-]?\s*render\s+'buy-buttons'", main) is not None, "main product must keep native product form")
require('"class": "section curved-section"' in main, "main product section must keep the shared curved-section authority")
require(re.search(r'<div class="curve-line-container">\s*<div class="curve-line"></div>\s*</div>', main, re.S) is not None, "main product must render the shared curve separator after its content")
require(re.search(r"\.curved-section\s+\.curve-line-container\s*\{[^}]*height:\s*60px", base_css, re.S) is not None, "global curve container geometry must remain available")
require(re.search(r"\.curved-section\s+\.curve-line\s*\{[^}]*height:\s*120px[^}]*border-radius:\s*50%", base_css, re.S) is not None, "global curve ellipse geometry must remain available")
require("<product-recommendations" in related, "related products must keep native recommendations element")
require("routes.product_recommendations_url" in related, "related products must use Shopify recommendations route")
require("recommendations.products" in related, "related cards must come from Shopify recommendation data")

page_local_source = f"{main}\n{related}"
require(re.search(r"<\s*(?:header|footer)\b", page_local_source, re.I) is None, "product sections must not duplicate global header or footer markup")
require(re.search(r"{%[-]?\s*sections?\s+['\"][^'\"]*(?:header|footer)[^'\"]*['\"]", page_local_source, re.I) is None, "product sections must not include global header or footer section groups")
require(re.search(r"{%[-]?\s*(?:render|include)\s+['\"][^'\"]*(?:header|footer)[^'\"]*['\"]", page_local_source, re.I) is None, "product sections must not render global header or footer snippets")
require(re.search(r"\b(?:wishlist|favorite|favourite|bookmark|save\s+product|heart(?:[-_\s]+(?:control|button|icon)))\b", page_local_source, re.I) is None, "product sections must not add an unowned wishlist, save-product, bookmark, or heart control")
require(not any(glyph in page_local_source for glyph in ("♡", "♥", "❤", "🖤", "🤍")), "product sections must not add an unowned interactive heart glyph")

require(related_settings.get("products_to_show") == 8, "product template must request eight recommendations")
require(related_settings.get("columns_desktop") == 4, "desktop recommendations must remain four columns")
require(related_settings.get("columns_mobile") == "1", "mobile recommendations must be exactly one product per row")
require("grid--{{ section.settings.columns_mobile }}-col-tablet-down" in related, "related grid must consume merchant mobile-column setting")

mobile_setting = next((setting for setting in related_schema.get("settings", []) if setting.get("id") == "columns_mobile"), {})
require(mobile_setting.get("type") == "select", "related products mobile columns must remain merchant-editable")
require(mobile_setting.get("default") == "1", "new related-products sections must default to one mobile column")
require({option.get("value") for option in mobile_setting.get("options", [])} == {"1", "2"}, "mobile column setting must preserve supported choices")

main_css_contract = [
    "/* Product detail Figma contract: 80846:313 */",
    "max-width: 144rem",
    "padding-inline: 8rem",
    "grid-template-columns: minmax(0, 575fr) minmax(0, 645fr)",
    "column-gap: 6rem",
    "aspect-ratio: 575 / 558",
    "font-size: 4.4rem",
    "font-size: 1.8rem",
]
for token in main_css_contract:
    require(token in main_css, f"main product CSS missing contract token: {token}")
require(re.search(r"@media\s+screen\s+and\s+\(min-width:\s*990px\).*?Product detail Figma contract", main_css, re.S) is not None, "main product Figma geometry must be desktop-scoped")
require(re.search(r"product-info\s+\.product--large:not\(\.product--no-media\)\s*\{[^}]*display:\s*grid[^}]*grid-template-columns:\s*minmax\(0,\s*575fr\)\s+minmax\(0,\s*645fr\)", main_css, re.S) is not None, "desktop Figma grid must apply only to merchant-selected large media size")
require(re.search(r"product-info\s+\.product:not\(\.product--no-media\)\s*\{[^}]*(?:display:\s*grid|grid-template-columns:)", main_css, re.S) is None, "desktop CSS must not add a competing broad grid that overrides medium or small merchant media sizes")
require(re.search(r"\.product-media-container\.constrain-height\s+\.media\s*\{[^}]*position:\s*relative[^}]*aspect-ratio:\s*575\s*/\s*558", main_css, re.S) is not None, "desktop product media must own the Figma aspect ratio without depending on a zero-height modal opener")
require(re.search(r"@media\s+screen\s+and\s+\(max-width:\s*749px\).*?product-info\s*>\s*\.page-width\s*\{[^}]*padding-inline:\s*2rem", main_css, re.S) is not None, "mobile main product must use consistent 20px gutters")
require(re.search(r"@media\s+screen\s+and\s+\(max-width:\s*749px\).*?\.product__title\s*>\s*h1\s*\{[^}]*font-size:\s*3\.2rem", main_css, re.S) is not None, "mobile product H1 must use derived 32px scale")
require(re.search(r"@media\s+screen\s+and\s+\(max-width:\s*749px\).*?\.product__description(?:,|\s*\{).*?font-size:\s*1\.6rem", main_css, re.S) is not None, "mobile product description must use derived 16px scale")

related_css_contract = [
    "/* Product recommendations Figma contract: 80846:251 */",
    "max-width: 144rem",
    "padding-inline: 8rem",
    "column-gap: 3.2rem",
    "row-gap: 3.2rem",
    "min-height: 40.6rem",
    "flex: 0 0 28.6rem",
    "min-height: 12rem",
    "flex: 1 0 auto",
    "flex-basis: 100%",
    "width: 100%",
    "max-width: 100%",
]
for token in related_css_contract:
    require(token in related_css, f"related products CSS missing contract token: {token}")
require(re.search(r"(?<!-)\bmin-height:\s*40\.6rem", related_css) is not None, "desktop recommendation card must preserve the 40.6rem Figma target as a safe minimum height")
require(re.search(r"(?<!-)\bheight:\s*40\.6rem", related_css) is None, "desktop recommendation card must not hard-cap merchant-variable content at 40.6rem")
require("max-height:" not in related_css, "related product stylesheet must not add a max-height cap that can clip merchant-variable card content")
require(re.search(r"overflow:\s*(?:hidden|clip)", related_css) is None, "related product cards must not hide or clip native quick-add or merchant-variable content")
require(re.search(r"@media\s+screen\s+and\s+\(max-width:\s*749px\).*?flex-basis:\s*100%", related_css, re.S) is not None, "one-card-per-row rule must cover the full mobile range below 750px")
require(re.search(r"@media\s+screen\s+and\s+\(max-width:\s*749px\).*?\.related-products__heading\s*\{[^}]*font-size:\s*3\.2rem", related_css, re.S) is not None, "mobile recommendation heading must use derived 32px scale")
require(re.search(r"@media\s+screen\s+and\s+\(min-width:\s*750px\)\s*\{.*?\.related-products\s+\.product-grid\s*\{[^}]*--related-card-width:\s*calc\(\(100%\s*-\s*3\.2rem\)\s*/\s*2\)", related_css, re.S) is not None, "tablet recommendations must use a min-width-only two-column width authority so every fractional viewport below 990px is covered")
require(re.search(r"@media\s+screen\s+and\s+\(min-width:\s*750px\)\s+and\s+\(max-width:\s*989", related_css, re.S) is None, "tablet recommendations must not reintroduce a decimal max-width dead zone")
require(re.search(r"@media\s+screen\s+and\s+\(min-width:\s*990px\)", related_css) is not None, "desktop recommendations must retain an explicit 990px override")
for columns, gap_total in [(1, "0rem"), (2, "3.2rem"), (3, "6.4rem"), (4, "9.6rem"), (5, "12.8rem"), (6, "16rem")]:
    expected = "100%" if columns == 1 else f"calc((100% - {gap_total}) / {columns})"
    require(
        re.search(rf"\.related-products\s+\.grid--{columns}-col-desktop\s*\{{[^}}]*--related-card-width:\s*{re.escape(expected)}", related_css, re.S) is not None,
        f"desktop merchant {columns}-column option must set the exact related-card width",
    )
require(re.search(r"\.related-products\s+\.grid\.product-grid\s*>\s*\.grid__item\s*\{[^}]*flex-basis:\s*var\(--related-card-width\)[^}]*width:\s*var\(--related-card-width\)[^}]*max-width:\s*var\(--related-card-width\)", related_css, re.S) is not None, "recommendation items must consume one merchant-column width authority")

for forbidden in ["Cherry Tomato", "$9.99", "Sourced daily from Sydney"]:
    require(forbidden not in main and forbidden not in related, f"Figma demo content must not be hard-coded: {forbidden}")

if ERRORS:
    print("Product detail contract validation failed:")
    for error in ERRORS:
        print(f"- {error}")
    raise SystemExit(1)

print("Product detail native/Figma contract validation passed")
