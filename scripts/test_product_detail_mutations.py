from __future__ import annotations

import io
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = ("assets", "config", "layout", "locales", "sections", "snippets", "templates")
FILES = [
    "scripts/validate_product_detail.py",
    "docs/product-detail/shopify-section-map.md",
    "docs/product-detail/editor-schema-contract.json",
    "docs/product-detail/interaction-contract.json",
    "docs/product-detail/responsive-contract.json",
    "docs/product-detail/content-migration-contract.json",
    "docs/product-detail/file-ownership.json",
    "sections/main-product.liquid",
    "sections/related-products.liquid",
    "assets/section-main-product.css",
    "assets/section-related-products.css",
    "assets/base.css",
    "templates/product.json",
    "layout/theme.liquid",
]

MUTATIONS = [
    (
        "template mobile columns",
        "templates/product.json",
        '        "columns_mobile": "1",',
        '        "columns_mobile": "2",',
    ),
    (
        "schema mobile default",
        "sections/related-products.liquid",
        '      "default": "1",',
        '      "default": "2",',
    ),
    (
        "recommendations route authority",
        "sections/related-products.liquid",
        "routes.product_recommendations_url",
        "routes.collections_url",
    ),
    (
        "dynamic product title authority",
        "sections/main-product.liquid",
        "{{ product.title | escape }}",
        "Fresh Product",
        2,
    ),
    (
        "desktop media ratio",
        "assets/section-main-product.css",
        "aspect-ratio: 575 / 558",
        "aspect-ratio: 575 / 557",
        2,
    ),
    (
        "non-collapsing media owner",
        "assets/section-main-product.css",
        "position: relative;\n    width: 100%;\n    height: auto;\n    aspect-ratio: 575 / 558",
        "position: absolute;\n    width: 100%;\n    height: auto;\n    aspect-ratio: 575 / 558",
    ),
    (
        "mobile twenty-pixel gutter",
        "assets/section-main-product.css",
        "padding-inline: 2rem;",
        "padding-inline: 1.9rem;",
    ),
    (
        "mobile product heading scale",
        "assets/section-main-product.css",
        "font-size: 3.2rem;",
        "font-size: 3.1rem;",
    ),
    (
        "tablet two-column recommendations",
        "assets/section-related-products.css",
        ".related-products .product-grid {\n    --related-card-width: calc((100% - 3.2rem) / 2);",
        ".related-products .product-grid {\n    --related-card-width: calc((100% - 3.2rem) / 3);",
    ),
    (
        "gap-free fractional tablet cascade",
        "assets/section-related-products.css",
        "@media screen and (min-width: 750px) {",
        "@media screen and (min-width: 750px) and (max-width: 989.98px) {",
    ),
    (
        "desktop merchant-column override",
        "assets/section-related-products.css",
        ".related-products .grid--4-col-desktop {\n    --related-card-width: calc((100% - 9.6rem) / 4);\n  }",
        ".related-products .grid--4-col-desktop {\n    --related-card-width: calc((100% - 9.6rem) / 2);\n  }",
    ),
    (
        "merchant media-size scope",
        "assets/section-main-product.css",
        "product-info .product--large:not(.product--no-media) {",
        "product-info .product:not(.product--no-media) {",
    ),
    (
        "desktop recommendation card growth",
        "assets/section-related-products.css",
        "min-height: 40.6rem;",
        "height: 40.6rem;",
    ),
    (
        "merchant-variable recommendation content growth",
        "assets/section-related-products.css",
        "min-height: 12rem;\n    flex: 1 0 auto;",
        "height: 12rem;\n    flex: 0 0 12rem;\n    overflow: hidden;",
    ),
    (
        "fake wishlist ownership",
        "sections/main-product.liquid",
        "<product-info\n",
        '<button class="wishlist" type="button">Save product</button>\n<product-info\n',
    ),
    (
        "duplicate global header ownership",
        "sections/related-products.liquid",
        "<product-recommendations",
        '<header class="product-header-copy"></header>\n<product-recommendations',
    ),
    (
        "keyword-free heart control",
        "sections/main-product.liquid",
        "<product-info\n",
        '<button class="heart-control" aria-label="Save product">♡</button>\n<product-info\n',
    ),
    (
        "plural header-group shell ownership",
        "sections/related-products.liquid",
        "<product-recommendations",
        "{% sections 'header-group' %}\n<product-recommendations",
    ),
    (
        "plural footer-group shell ownership",
        "sections/related-products.liquid",
        "<product-recommendations",
        "{% sections 'footer-group' %}\n<product-recommendations",
    ),
    (
        "additive broad media-size grid",
        "assets/section-main-product.css",
        "  /* Product detail Figma contract: 80846:313 */",
        "  product-info .product:not(.product--no-media) { display: grid; grid-template-columns: 1fr 1fr; }\n\n  /* Product detail Figma contract: 80846:313 */",
    ),
    (
        "desktop recommendation max-height cap",
        "assets/section-related-products.css",
        "min-height: 40.6rem;",
        "min-height: 40.6rem;\n    max-height: 40.6rem;",
    ),
    (
        "encoded heart entity control",
        "sections/main-product.liquid",
        "<product-info\n",
        '<button aria-label="Add">&#9825;</button>\n<product-info\n',
    ),
    (
        "unlisted colored heart control",
        "sections/main-product.liquid",
        "<product-info\n",
        '<button aria-label="Add">💚</button>\n<product-info\n',
    ),
    (
        "keyword-free star save control",
        "sections/main-product.liquid",
        "<product-info\n",
        '<button aria-label="Save">★</button>\n<product-info\n',
    ),
    (
        "whitespace max-height cap",
        "assets/section-related-products.css",
        "min-height: 40.6rem;",
        "min-height: 40.6rem;\n    max-height : 40.6rem;",
    ),
    (
        "whitespace overflow clip",
        "assets/section-related-products.css",
        "min-height: 40.6rem;",
        "min-height: 40.6rem;\n    overflow : clip;",
    ),
    (
        "unscoped broad media grid",
        "assets/section-main-product.css",
        "  /* Product detail Figma contract: 80846:313 */",
        "  .product:not(.product--no-media) { display: grid; grid-template-columns: 1fr 1fr; }\n\n  /* Product detail Figma contract: 80846:313 */",
    ),
    (
        "is-wrapped broad media grid",
        "assets/section-main-product.css",
        "  /* Product detail Figma contract: 80846:313 */",
        "  product-info :is(.product:not(.product--no-media)) { display: grid; grid-template-columns: 1fr 1fr; }\n\n  /* Product detail Figma contract: 80846:313 */",
    ),
    (
        "important competing recommendation width",
        "assets/section-related-products.css",
        "/* Product recommendations Figma contract: 80846:251 */",
        ".related-products .grid.product-grid > .grid__item { width: 100% !important; }\n\n/* Product recommendations Figma contract: 80846:251 */",
    ),
    (
        "arbitrary static recommendation card",
        "sections/related-products.liquid",
        "<product-recommendations",
        '<ul><li class="grid__item">Static Pear $12.00</li></ul>\n<product-recommendations',
    ),
    (
        "global base competing recommendation width",
        "assets/base.css",
        ".curved-section .curve-line-container {",
        ".related-products .grid.product-grid > .grid__item { width: 100% !important; }\n\n.curved-section .curve-line-container {",
    ),
    (
        "template custom-liquid static card and save control",
        "templates/product.json",
        '        "share": {\n          "type": "share",\n          "disabled": true,\n          "settings": {\n            "share_label": "Share"\n          }\n        }\n      },\n      "block_order": [\n        "vendor",',
        '        "share": {\n          "type": "share",\n          "disabled": true,\n          "settings": {\n            "share_label": "Share"\n          }\n        },\n        "qa-static": {\n          "type": "custom_liquid",\n          "settings": {\n            "custom_liquid": "<div>Static Pear $12.00<button aria-label=\\"Save\\">★</button></div>"\n          }\n        }\n      },\n      "block_order": [\n        "qa-static",\n        "vendor",',
    ),
    (
        "theme layout stylesheet loader drift",
        "layout/theme.liquid",
        "{{ 'base.css' | asset_url | stylesheet_tag }}",
        "{{ 'base.css' | asset_url | stylesheet_tag }}\n{{ 'component-card.css' | asset_url | stylesheet_tag }}",
    ),
    (
        "transitive component-card width override",
        "assets/component-card.css",
        ".card-wrapper {",
        ".related-products .grid__item { width: 100% !important; }\n\n.card-wrapper {",
    ),
    (
        "global script injected fake save control",
        "assets/global.js",
        "function getFocusableElements(container) {",
        "document.addEventListener('DOMContentLoaded', () => document.querySelector('product-info')?.insertAdjacentHTML('beforeend', '<button>★</button>'));\n\nfunction getFocusableElements(container) {",
    ),
    (
        "transitive card snippet static sample",
        "snippets/card-product.liquid",
        "{% comment %}\n  Renders a product card",
        "<div>Static Pear $12.00</div>\n{% comment %}\n  Renders a product card",
    ),
    (
        "main product curve markup",
        "sections/main-product.liquid",
        '<div class="curve-line-container">',
        '<div class="curve-line-container-disabled">',
    ),
    (
        "shared curve ellipse geometry",
        "assets/base.css",
        ".curved-section .curve-line {",
        ".curved-section .curve-line-disabled {",
    ),
    (
        "forbidden Figma demo content",
        "sections/related-products.liquid",
        "{{ section.settings.heading }}",
        "{{ section.settings.heading }} Cherry Tomato",
    ),
]


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/validate_product_detail.py"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def copy_fixture(destination: Path) -> None:
    for runtime_root in RUNTIME_ROOTS:
        shutil.copytree(ROOT / runtime_root, destination / runtime_root, dirs_exist_ok=True)
    for relative in FILES:
        if relative.split("/", 1)[0] in RUNTIME_ROOTS:
            continue
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def run_topology_probes() -> subprocess.CompletedProcess[str]:
    if os.name == "nt":
        if shutil.which("wsl.exe") is None:
            return subprocess.CompletedProcess([], 125, "WSL2 is required for no-follow topology probes on Windows")
        fixture = f"/tmp/freshclub-product-topology-{uuid.uuid4().hex}"
        archive_bytes = io.BytesIO()
        with tarfile.open(fileobj=archive_bytes, mode="w") as archive:
            for runtime_root in RUNTIME_ROOTS:
                archive.add(ROOT / runtime_root, arcname=runtime_root, recursive=True)
            archive.add(ROOT / "scripts/validate_product_detail.py", arcname="scripts/validate_product_detail.py")
            archive.add(ROOT / "docs/product-detail", arcname="docs/product-detail", recursive=True)
        create = subprocess.run(["wsl.exe", "mkdir", "-p", fixture], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if create.returncode != 0:
            return subprocess.CompletedProcess(create.args, 125, create.stdout.decode("utf-8", errors="replace"))
        try:
            extract = subprocess.run(
                ["wsl.exe", "tar", "-xf", "-", "-C", fixture],
                input=archive_bytes.getvalue(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if extract.returncode != 0:
                return subprocess.CompletedProcess(extract.args, 125, extract.stdout.decode("utf-8", errors="replace"))
            script = f"""set -eu
cd {shlex.quote(fixture)}
python3 scripts/validate_product_detail.py >/dev/null
cp assets/base.css outside-base.css
rm assets/base.css
ln -s {shlex.quote(fixture + '/outside-base.css')} assets/base.css
if python3 scripts/validate_product_detail.py >/dev/null 2>&1; then echo 'same-byte symlink substitution accepted'; exit 41; fi
rm assets/base.css
ln outside-base.css assets/base.css
if python3 scripts/validate_product_detail.py >/dev/null 2>&1; then echo 'same-byte hardlink substitution accepted'; exit 42; fi
rm assets/base.css
cp outside-base.css assets/base.css
mv assets outside-assets
ln -s {shlex.quote(fixture + '/outside-assets')} assets
if python3 scripts/validate_product_detail.py >/dev/null 2>&1; then echo 'symlinked runtime directory accepted'; exit 43; fi
rm assets
mv outside-assets assets
mv locales outside-locales
ln -s {shlex.quote(fixture + '/outside-locales')} locales
if python3 scripts/validate_product_detail.py >/dev/null 2>&1; then echo 'symlinked runtime root accepted'; exit 44; fi
rm locales
mv outside-locales locales
mkfifo assets/qa-nonregular
if python3 scripts/validate_product_detail.py >/dev/null 2>&1; then echo 'FIFO runtime entry accepted'; exit 45; fi
rm assets/qa-nonregular
cp -a assets race-outside-assets
python3 - <<'PY'
from pathlib import Path
path = Path('scripts/validate_product_detail.py')
source = path.read_text(encoding='utf-8')
needle = '                    runtime_root_fd = os.open(root_name, directory_flags, dir_fd=root_fd)\\n'
replacement = needle + '                    if root_name == "assets":\\n                        print("RACE_READY", flush=True)\\n                        __import__("time").sleep(1)\\n'
if source.count(needle) != 1:
    raise SystemExit('race probe seam missing')
path.write_text(source.replace(needle, replacement), encoding='utf-8')
PY
python3 scripts/validate_product_detail.py >race-validator.log 2>&1 &
race_pid=$!
race_ready=0
for _ in $(seq 1 100); do
  if grep -q RACE_READY race-validator.log; then race_ready=1; break; fi
  sleep 0.02
done
if [ "$race_ready" -ne 1 ]; then echo 'descriptor race probe did not reach pause'; kill "$race_pid" 2>/dev/null || true; exit 46; fi
mv assets race-original-assets
ln -s {shlex.quote(fixture + '/race-outside-assets')} assets
set +e
wait "$race_pid"
race_status=$?
set -e
if [ "$race_status" -eq 0 ]; then echo 'parent-path replacement during scan accepted'; exit 47; fi
echo 'PASS topology rejected: same-byte symlink substitution'
echo 'PASS topology rejected: same-byte hardlink substitution'
echo 'PASS topology rejected: symlinked runtime directory'
echo 'PASS topology rejected: symlinked runtime root'
echo 'PASS topology rejected: FIFO runtime entry'
echo 'PASS topology rejected: parent-path replacement during descriptor scan'
"""
            completed = subprocess.run(
                ["wsl.exe", "sh", "-s"],
                input=script.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            return subprocess.CompletedProcess(
                completed.args,
                completed.returncode,
                completed.stdout.decode("utf-8", errors="replace"),
            )
        finally:
            subprocess.run(["wsl.exe", "rm", "-rf", fixture], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    with tempfile.TemporaryDirectory(prefix="freshclub-product-topology-") as temp_dir:
        fixture = Path(temp_dir) / "fixture"
        fixture.mkdir()
        copy_fixture(fixture)
        baseline = run_validator(fixture)
        if baseline.returncode != 0:
            return baseline
        outside = Path(temp_dir) / "outside-base.css"
        outside.write_bytes((fixture / "assets/base.css").read_bytes())
        base = fixture / "assets/base.css"
        base.unlink()
        base.symlink_to(outside)
        symlink_result = run_validator(fixture)
        if symlink_result.returncode == 0:
            return subprocess.CompletedProcess([], 41, "same-byte symlink substitution accepted")
        base.unlink()
        os.link(outside, base)
        hardlink_result = run_validator(fixture)
        if hardlink_result.returncode == 0:
            return subprocess.CompletedProcess([], 42, "same-byte hardlink substitution accepted")
        base.unlink()
        shutil.copy2(outside, base)
        assets = fixture / "assets"
        outside_assets = Path(temp_dir) / "outside-assets"
        assets.rename(outside_assets)
        assets.symlink_to(outside_assets, target_is_directory=True)
        if run_validator(fixture).returncode == 0:
            return subprocess.CompletedProcess([], 43, "symlinked runtime directory accepted")
        assets.unlink()
        outside_assets.rename(assets)
        locales = fixture / "locales"
        outside_locales = Path(temp_dir) / "outside-locales"
        locales.rename(outside_locales)
        locales.symlink_to(outside_locales, target_is_directory=True)
        if run_validator(fixture).returncode == 0:
            return subprocess.CompletedProcess([], 44, "symlinked runtime root accepted")
        locales.unlink()
        outside_locales.rename(locales)
        fifo = assets / "qa-nonregular"
        os.mkfifo(fifo)
        if run_validator(fixture).returncode == 0:
            return subprocess.CompletedProcess([], 45, "FIFO runtime entry accepted")
        fifo.unlink()
        validator_path = fixture / "scripts/validate_product_detail.py"
        validator_source = validator_path.read_text(encoding="utf-8")
        race_needle = '                    runtime_root_fd = os.open(root_name, directory_flags, dir_fd=root_fd)\n'
        race_replacement = race_needle + '                    if root_name == "assets":\n                        print("RACE_READY", flush=True)\n                        __import__("time").sleep(1)\n'
        if validator_source.count(race_needle) != 1:
            return subprocess.CompletedProcess([], 46, "descriptor race probe seam missing")
        validator_path.write_text(validator_source.replace(race_needle, race_replacement), encoding="utf-8")
        race_outside_assets = Path(temp_dir) / "race-outside-assets"
        shutil.copytree(assets, race_outside_assets)
        race_process = subprocess.Popen(
            [sys.executable, "scripts/validate_product_detail.py"],
            cwd=fixture,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        ready = False
        race_output: list[str] = []
        assert race_process.stdout is not None
        for line in race_process.stdout:
            race_output.append(line)
            if "RACE_READY" in line:
                ready = True
                break
        if not ready:
            race_process.kill()
            return subprocess.CompletedProcess([], 46, "descriptor race probe did not reach pause: " + "".join(race_output))
        race_original_assets = Path(temp_dir) / "race-original-assets"
        assets.rename(race_original_assets)
        assets.symlink_to(race_outside_assets, target_is_directory=True)
        remainder, _ = race_process.communicate(timeout=10)
        race_output.append(remainder)
        if race_process.returncode == 0:
            return subprocess.CompletedProcess([], 47, "parent-path replacement during scan accepted: " + "".join(race_output))
        return subprocess.CompletedProcess(
            [],
            0,
            "PASS topology rejected: same-byte symlink substitution\nPASS topology rejected: same-byte hardlink substitution\nPASS topology rejected: symlinked runtime directory\nPASS topology rejected: symlinked runtime root\nPASS topology rejected: FIFO runtime entry\nPASS topology rejected: parent-path replacement during descriptor scan\n",
        )


def main() -> None:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="freshclub-product-mutations-") as temp_dir:
        fixture = Path(temp_dir)
        copy_fixture(fixture)

        baseline = run_validator(fixture)
        if baseline.returncode != 0:
            raise SystemExit(f"mutation baseline failed:\n{baseline.stdout}")

        for mutation in MUTATIONS:
            name, relative, old, new, *expected_values = mutation
            expected_count = expected_values[0] if expected_values else 1
            target = fixture / relative
            original = target.read_text(encoding="utf-8")
            count = original.count(old)
            if count != expected_count:
                failures.append(f"{name}: expected {expected_count} mutation seam(s), found {count}")
                continue
            target.write_text(original.replace(old, new), encoding="utf-8", newline="")
            result = run_validator(fixture)
            target.write_text(original, encoding="utf-8", newline="")
            if result.returncode == 0:
                failures.append(f"{name}: validator accepted mutation")
            else:
                print(f"PASS mutation rejected: {name}")

    topology = run_topology_probes()
    if topology.returncode != 0:
        failures.append(f"runtime topology probes failed ({topology.returncode}): {topology.stdout.strip()}")
    else:
        print(topology.stdout.strip())

    if failures:
        print("Product detail mutation suite failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print(f"Product detail mutation suite passed ({len(MUTATIONS) + 6} rejected adversarial cases: {len(MUTATIONS)} content/inventory and 6 topology/race)")


if __name__ == "__main__":
    main()
