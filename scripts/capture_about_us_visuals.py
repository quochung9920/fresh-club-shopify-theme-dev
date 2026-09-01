#!/usr/bin/env python
"""Capture deterministic About Us reference/candidate screenshots with raw CDP."""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket
from PIL import Image, ImageChops, ImageStat

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "prototype" / "about-us" / "notes" / "visual"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PAGES = {
    "reference": "http://127.0.0.1:4174/reference-local.html",
    "candidate": "http://127.0.0.1:4174/index.html",
    "liquid-fixture": "http://127.0.0.1:4174/liquid-css-fixture.html",
}
VIEWPORTS = (375, 390, 768, 1440)
MAX_MEAN_CHANNEL_DELTA = 0.005


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class CDP:
    def __init__(self, ws_url: str) -> None:
        self.ws = websocket.create_connection(ws_url, timeout=30, origin="http://127.0.0.1")
        self.next_id = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        request_id = self.next_id
        self.ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            payload = json.loads(self.ws.recv())
            if payload.get("id") != request_id:
                continue
            if "error" in payload:
                raise RuntimeError(f"CDP {method}: {payload['error']}")
            return payload.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = False):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
            },
        )
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result["result"].get("value")

    def close(self) -> None:
        self.ws.close()


def wait_json(url: str, timeout: float = 15) -> dict:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.load(response)
        except Exception as error:  # pragma: no cover - diagnostic path
            last_error = error
            time.sleep(0.1)
    raise RuntimeError(f"Chrome CDP did not become ready: {last_error}")


def create_tab(port: int, url: str) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe=':/?=&')}",
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def capture(cdp: CDP, label: str, url: str, width: int) -> dict:
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")
    cdp.call("Log.enable")
    cdp.call(
        "Emulation.setDeviceMetricsOverride",
        {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width <= 768},
    )
    cdp.call(
        "Emulation.setEmulatedMedia",
        {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]},
    )
    cdp.call("Page.navigate", {"url": url})
    deadline = time.time() + 20
    while time.time() < deadline:
        if cdp.evaluate("document.readyState") == "complete":
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"Page did not finish loading: {url}")
    cdp.evaluate("document.fonts.ready.then(() => true)", await_promise=True)
    deadline = time.time() + 20
    while time.time() < deadline:
        if cdp.evaluate("[...document.images].every((image) => image.complete && image.naturalWidth > 0)"):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"Images did not finish loading: {url}")
    time.sleep(0.25)

    metrics = cdp.evaluate(
        """(() => ({
          title: document.title,
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          scrollHeight: document.documentElement.scrollHeight,
          bodyHeight: document.body.getBoundingClientRect().height,
          fontStatus: document.fonts.status,
          rootFont: getComputedStyle(document.body).fontFamily,
          duplicateIds: [...document.querySelectorAll('[id]')]
            .map((el) => el.id).filter((id, index, all) => all.indexOf(id) !== index),
          sections: [...document.querySelectorAll('header, main > section, main > .cta-wrap, main > .fc-cta-wrap, footer')]
            .map((el) => ({
              selector: el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().replace(/\\s+/g, '.') : ''),
              top: el.getBoundingClientRect().top + scrollY,
              height: el.getBoundingClientRect().height
            })),
          images: [...document.images].map((image) => ({
            src: image.currentSrc || image.src,
            complete: image.complete,
            naturalWidth: image.naturalWidth,
            naturalHeight: image.naturalHeight
          }))
        }))()"""
    )
    if metrics["clientWidth"] != width:
        raise RuntimeError(f"Viewport mismatch: requested {width}, rendered {metrics['clientWidth']}")
    if metrics["scrollWidth"] > width:
        raise RuntimeError(
            f"Horizontal overflow at {width}: scrollWidth={metrics['scrollWidth']}"
        )
    if metrics["fontStatus"] != "loaded":
        raise RuntimeError(f"Fonts are not loaded at {width}: {url}")
    if metrics["duplicateIds"]:
        raise RuntimeError(f"Duplicate IDs at {width}: {metrics['duplicateIds']}")
    if len(metrics["sections"]) != 8:
        raise RuntimeError(f"Unexpected section count at {width}: {url}")

    screenshot = cdp.call(
        "Page.captureScreenshot",
        {
            "format": "png",
            "captureBeyondViewport": True,
            "fromSurface": True,
            "clip": {
                "x": 0,
                "y": 0,
                "width": width,
                "height": metrics["scrollHeight"],
                "scale": 1,
            },
        },
    )
    png = base64.b64decode(screenshot["data"])
    destination = OUTPUT / f"{label}-{width}.png"
    destination.write_bytes(png)
    metrics.update(
        {
            "url": url,
            "screenshot": destination.relative_to(REPO).as_posix(),
            "screenshotBytes": len(png),
            "screenshotSha256": hashlib.sha256(png).hexdigest(),
        }
    )
    return metrics


def compare(reference: Path, candidate: Path) -> dict:
    with Image.open(reference).convert("RGB") as ref, Image.open(candidate).convert("RGB") as cand:
        result = {
            "referenceDimensions": list(ref.size),
            "candidateDimensions": list(cand.size),
            "equalDimensions": ref.size == cand.size,
        }
        if ref.size != cand.size:
            result.update(
                {
                    "diffBoundingBox": None,
                    "meanPerChannelDelta": None,
                    "pixelIdentical": False,
                    "maxMeanChannelDelta": MAX_MEAN_CHANNEL_DELTA,
                    "withinTolerance": False,
                }
            )
            return result
        diff = ImageChops.difference(ref, cand)
        stat = ImageStat.Stat(diff)
        bbox = diff.getbbox()
        mean_delta = [round(value, 6) for value in stat.mean]
        result.update(
            {
                "diffBoundingBox": list(bbox) if bbox else None,
                "meanPerChannelDelta": mean_delta,
                "pixelIdentical": bbox is None,
                "maxMeanChannelDelta": MAX_MEAN_CHANNEL_DELTA,
                "withinTolerance": max(mean_delta) <= MAX_MEAN_CHANNEL_DELTA,
            }
        )
        diff_stem = candidate.stem.replace("candidate", "diff").replace(
            "liquid-fixture", "liquid-fixture-diff"
        )
        diff.save(candidate.with_name(diff_stem + ".png"))
        return result


def main() -> int:
    if not CHROME.is_file():
        raise SystemExit(f"Chrome not found: {CHROME}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    with tempfile.TemporaryDirectory(prefix="freshclub-cdp-") as profile:
        process = subprocess.Popen(
            [
                str(CHROME),
                "--headless=new",
                f"--remote-debugging-port={port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--disable-extensions",
                "--disable-background-networking",
                "--hide-scrollbars",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_json(f"http://127.0.0.1:{port}/json/version")
            tab = create_tab(port, "about:blank")
            cdp = CDP(tab["webSocketDebuggerUrl"])
            try:
                captures = []
                for width in VIEWPORTS:
                    for label, url in PAGES.items():
                        captures.append(capture(cdp, label, url, width))
            finally:
                cdp.close()
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    comparisons = {}
    liquid_fixture_comparisons = {}
    for width in VIEWPORTS:
        comparisons[str(width)] = compare(
            OUTPUT / f"reference-{width}.png", OUTPUT / f"candidate-{width}.png"
        )
        liquid_fixture_comparisons[str(width)] = compare(
            OUTPUT / f"reference-{width}.png", OUTPUT / f"liquid-fixture-{width}.png"
        )
    capture_evidence = [
        {
            "screenshot": capture_item["screenshot"],
            "screenshotBytes": capture_item["screenshotBytes"],
            "screenshotSha256": capture_item["screenshotSha256"],
        }
        for capture_item in captures
    ]
    result = {
        "captures": capture_evidence,
        "comparisons": comparisons,
        "liquidFixtureComparisons": liquid_fixture_comparisons,
    }
    output = OUTPUT / "visual-results.json"
    output.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
