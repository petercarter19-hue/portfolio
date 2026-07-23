"""Capture the complete 15-state Community Feed/The Break evidence matrix."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import app


def _resolve_chrome():
    """Resolve a real Chrome executable across the machines this harness runs on.

    Honors an explicit PEERSLATE_CHROME override first, then probes the known
    Mac and Windows install paths in order. Returns None (never a guessed or
    fabricated path) when no real executable is found, so callers keep an
    honest skip/exit instead of pointing Playwright at a nonexistent binary.
    """
    override = os.environ.get("PEERSLATE_CHROME")
    if override and os.path.exists(override):
        return override
    for candidate in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.exists(candidate):
            return candidate
    return None


CHROME = _resolve_chrome()
OUT = Path(
    os.environ.get(
        "PEERSLATE_COMMUNITY_EVIDENCE_OUT",
        ROOT / "artifacts" / "ps-community-journal-home-milestone-001" / "community",
    )
)


CAPTURES = (
    ("break__route-the-slate__state-feed-keyboard-switch-focus__vp-1440x1000__theme-light__region-top.png", "/the-slate", 1440, 1000, False, "keyboard-focus", "top"),
    ("break__route-the-slate-break__state-direct__vp-1440x1000__theme-dark__region-lower.png", "/the-slate/break", 1440, 1000, True, "break", "lower"),
    ("break__route-the-slate-break__state-direct__vp-1440x1000__theme-dark__region-top.png", "/the-slate/break", 1440, 1000, True, "break", "top"),
    ("break__route-the-slate-break__state-direct__vp-1440x1000__theme-light__region-lower.png", "/the-slate/break", 1440, 1000, False, "break", "lower"),
    ("break__route-the-slate-break__state-direct__vp-1440x1000__theme-light__region-top.png", "/the-slate/break", 1440, 1000, False, "break", "top"),
    ("break__route-the-slate-break__state-direct__vp-320x800__theme-dark__region-top.png", "/the-slate/break", 320, 800, True, "break", "top"),
    ("break__route-the-slate-break__state-direct__vp-320x800__theme-light__region-top.png", "/the-slate/break", 320, 800, False, "break", "top"),
    ("break__route-the-slate-break__state-direct__vp-390x844__theme-dark__region-lower.png", "/the-slate/break", 390, 844, True, "break", "lower"),
    ("break__route-the-slate-break__state-direct__vp-390x844__theme-dark__region-top.png", "/the-slate/break", 390, 844, True, "break", "top"),
    ("break__route-the-slate-break__state-direct__vp-390x844__theme-light__region-lower.png", "/the-slate/break", 390, 844, False, "break", "lower"),
    ("break__route-the-slate-break__state-direct__vp-390x844__theme-light__region-top.png", "/the-slate/break", 390, 844, False, "break", "top"),
    ("feed__route-the-slate__state-loaded__vp-1440x1000__theme-dark__region-top.png", "/the-slate", 1440, 1000, True, "feed", "top"),
    ("feed__route-the-slate__state-loaded__vp-1440x1000__theme-light__region-top.png", "/the-slate", 1440, 1000, False, "feed", "top"),
    ("feed__route-the-slate__state-loaded__vp-390x844__theme-dark__region-top.png", "/the-slate", 390, 844, True, "feed", "top"),
    ("feed__route-the-slate__state-loaded__vp-390x844__theme-light__region-top.png", "/the-slate", 390, 844, False, "feed", "top"),
)


def main() -> None:
    if not CHROME:
        raise SystemExit(
            "Chrome is required (set PEERSLATE_CHROME, or install at a known "
            "Mac/Windows path)"
        )
    OUT.mkdir(parents=True, exist_ok=True)
    prior_testing = app.config.get("TESTING")
    app.config["TESTING"] = True
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    captures = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROME, headless=True)
            for name, start_path, width, height, dark, state, region in CAPTURES:
                context = browser.new_context(viewport={"width": width, "height": height})
                if dark:
                    context.add_init_script("localStorage.setItem('ps-theme', 'dark');")
                page = context.new_page()
                page.goto(f"{base_url}{start_path}", wait_until="networkidle")
                page.wait_for_function("document.querySelectorAll('#feedColumn [data-post]').length >= 3")

                if state == "keyboard-focus":
                    page.locator("#tab-feed").focus()
                    page.keyboard.press("ArrowRight")
                    page.wait_for_url(f"{base_url}/the-slate/break")
                    page.wait_for_function(
                        "document.activeElement && document.activeElement.id === 'tab-break'"
                    )
                elif region == "lower":
                    page.locator(".bk-quote").scroll_into_view_if_needed()
                    page.evaluate("window.scrollBy(0, -24)")
                else:
                    page.evaluate("window.scrollTo(0, 0)")

                page.wait_for_function(
                    """() => Array.from(document.images).every((image) => {
                        const rect = image.getBoundingClientRect();
                        const nearViewport = rect.bottom >= -1000 && rect.top <= innerHeight + 1000;
                        const rendered = rect.width > 0 && rect.height > 0;
                        return !rendered || !nearViewport || (image.complete && image.naturalWidth > 0);
                    })"""
                )
                page.wait_for_timeout(100)
                expected_panel = "#mainInner" if state == "feed" else "#panel-break"
                expected_tab = "#tab-feed" if state == "feed" else "#tab-break"
                assertions = page.evaluate(
                    """([panelSelector, tabSelector, isKeyboard, region]) => {
                        const panel = document.querySelector(panelSelector);
                        const tab = document.querySelector(tabSelector);
                        const focusStyle = getComputedStyle(tab);
                        return {
                            location_pathname: location.pathname,
                            active_tab: document.querySelector('[role="tab"][aria-selected="true"]')?.dataset.commTab || null,
                            focused_tab: document.activeElement?.dataset?.commTab || null,
                            expected_panel_visible: !!panel && !panel.hidden,
                            expected_tab_selected: tab?.getAttribute('aria-selected') === 'true',
                            feed_content_ready: document.body.textContent.includes('Dinner has been served!'),
                            feed_post_count: document.querySelectorAll('#feedColumn [data-post]').length,
                            focus_ring_visible: isKeyboard && focusStyle.outlineStyle !== 'none' && parseFloat(focusStyle.outlineWidth) > 0,
                            region_anchor: region === 'lower' ? '.bk-quote' : null,
                            scroll_y: Math.round(scrollY),
                            required_visible_content: region === 'lower' ? [
                                document.body.textContent.includes('Mood Switch'),
                                document.body.textContent.includes('Pick-Me-Up')
                            ] : [],
                        };
                    }""",
                    [expected_panel, expected_tab, state == "keyboard-focus", region],
                )
                if not assertions["expected_panel_visible"] or not assertions["expected_tab_selected"]:
                    raise RuntimeError(f"Community state assertion failed for {name}: {assertions}")
                if state == "keyboard-focus" and not assertions["focus_ring_visible"]:
                    raise RuntimeError(f"Community keyboard focus is not visible for {name}")
                if region == "lower" and not all(assertions["required_visible_content"]):
                    raise RuntimeError(f"Community lower content missing for {name}")
                page.screenshot(path=str(OUT / name), animations="disabled")
                captures.append(
                    {
                        "file": name,
                        "route": "/the-slate/break" if state != "feed" else "/the-slate",
                        "start_route": start_path,
                        "state": state,
                        "viewport": f"{width}x{height}",
                        "theme": "dark" if dark else "light",
                        "region": region,
                        "semantic_assertions": assertions,
                    }
                )
                context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        app.config["TESTING"] = prior_testing

    (OUT / "capture-log.json").write_text(
        json.dumps({"fixture": "sample Community; no persistence", "captures": captures}, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
