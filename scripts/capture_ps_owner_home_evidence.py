"""Capture the 21-state Owner Home milestone evidence matrix.

The harness uses only the flag-on private route and process-local Mock-backed
owner-home.v1 view models. It never connects to a database. The 200% proof is
an actual 720 CSS-pixel viewport (1440 physical pixels / 2), not CSS ``zoom``
and not a page-scale screenshot that widens the decoded canvas.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import app
from services.owner_home_service import OwnerHomeContractError, OwnerHomeService


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
        "PEERSLATE_OWNER_HOME_EVIDENCE_OUT",
        ROOT / "artifacts" / "ps-community-journal-home-milestone-001" / "owner_home",
    )
)
FIXED_CLOCK = lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc)


def _owner_row(display_name: str, profile_key: str = "11111111-1111-1111-1111-111111111111"):
    return {
        "profile_key": profile_key,
        "display_name": display_name,
        "profile_row_version": "01" * 8,
    }


def _review_row(item_key: str, kind: str, status: str, minute: int, token: str):
    return {
        "item_key": item_key,
        "review_kind": kind,
        "created_at_utc": f"2026-07-20T10:{minute:02d}:00",
        "updated_at_utc": f"2026-07-20T10:{minute + 1:02d}:00",
        "version_token": token * 8,
        "status": status,
    }


def _moment_row(moment_key: str, title: str):
    return {
        "moment_key": moment_key,
        "confirmed_version": 2,
        "title": title,
        "occurred_on": "2026-07-19",
        "updated_at_utc": "2026-07-20T10:40:00",
        "version_token": "05" * 8,
        "status": "confirmed",
    }


def _view_model(mode: str):
    owner_name = "Owner A"
    profile_key = "11111111-1111-1111-1111-111111111111"
    failed_key = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    proposal_key = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    ready_key = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    moment_key = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    title = "A real confirmed Moment"

    if mode == "long-bidi":
        owner_name = "ليلى כהן — Owner with a deliberately bounded long display name"
        title = "قصة مهنية طويلة ومحدودة — סיפור מקצועי ארוך — a confirmed Moment that proves wrapping without leaking or overflowing"
    elif mode == "priya":
        owner_name = "Priya Shah"
        profile_key = "31111111-1111-1111-1111-111111111111"
        failed_key = "3aaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        proposal_key = "3bbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        ready_key = "3ccccccc-cccc-cccc-cccc-cccccccccccc"
        moment_key = "3ddddddd-dddd-dddd-dddd-dddddddddddd"
        title = "Priya's confirmed launch Moment"
    elif mode == "noah":
        owner_name = "Noah Kim"
        profile_key = "41111111-1111-1111-1111-111111111111"
        failed_key = "4aaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        proposal_key = "4bbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        ready_key = "4ccccccc-cccc-cccc-cccc-cccccccccccc"
        moment_key = "4ddddddd-dddd-dddd-dddd-dddddddddddd"
        title = "Noah's confirmed mentoring Moment"

    if mode == "empty":
        result_sets = [[_owner_row(owner_name, profile_key)], [], []]
    else:
        result_sets = [
            [_owner_row(owner_name, profile_key)],
            [
                _review_row(failed_key, "voice_draft_failed", "failed", 1, "02"),
                _review_row(proposal_key, "moment_proposal_pending", "proposal", 2, "03"),
                _review_row(ready_key, "voice_draft_ready", "needs_review", 3, "04"),
            ],
            [_moment_row(moment_key, title)],
        ]
    database = Mock()
    database.execute_procedure.return_value = result_sets
    return OwnerHomeService(database=database, clock=FIXED_CLOCK).get_home(
        SimpleNamespace(user_key=f"evidence-{mode}")
    )


class _Provider:
    mode = "populated"

    def get_home(self, _identity):
        if self.mode == "failure":
            raise OwnerHomeContractError("synthetic evidence failure")
        return _view_model(self.mode)


def _assert_reflow_geometry(page):
    geometry = page.evaluate(
        """() => {
            const selectors = ['.oh__header', '.oh__nav', '.oh__capture-card', '.oh__stage'];
            const boxes = Object.fromEntries(selectors.map((selector) => {
                const node = document.querySelector(selector);
                if (!node) return [selector, null];
                const rect = node.getBoundingClientRect();
                const style = getComputedStyle(node);
                return [selector, {
                    left: Math.round(rect.left), right: Math.round(rect.right),
                    top: Math.round(rect.top), bottom: Math.round(rect.bottom),
                    width: Math.round(rect.width), height: Math.round(rect.height),
                    visible: style.display !== 'none' && style.visibility !== 'hidden' &&
                        rect.width > 0 && rect.height > 0,
                    horizontally_clipped: rect.left < 0 || rect.right > innerWidth,
                }];
            }));
            const hero = document.querySelector('.oh__hero').getBoundingClientRect();
            const capture = document.querySelector('.oh__capture-card').getBoundingClientRect();
            const overlaps = !(
                hero.right <= capture.left || capture.right <= hero.left ||
                hero.bottom <= capture.top || capture.bottom <= hero.top
            );
            const focused = document.activeElement;
            const focusedStyle = focused ? getComputedStyle(focused) : null;
            return {
                css_viewport: `${innerWidth}x${innerHeight}`,
                document_client_width: document.documentElement.clientWidth,
                document_scroll_width: document.documentElement.scrollWidth,
                horizontal_overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
                essential_boxes: boxes,
                hero_capture_overlap: overlaps,
                focused_selector: focused && focused.matches('.oh__capture-card') ? '.oh__capture-card' : null,
                focus_outline_visible: !!focusedStyle && focusedStyle.outlineStyle !== 'none' &&
                    parseFloat(focusedStyle.outlineWidth) > 0,
            };
        }"""
    )
    if geometry["css_viewport"] != "720x450":
        raise RuntimeError(f"unexpected 200% CSS viewport: {geometry['css_viewport']}")
    if geometry["horizontal_overflow"]:
        raise RuntimeError("Owner Home 200% proof has horizontal document overflow")
    if geometry["hero_capture_overlap"]:
        raise RuntimeError("Owner Home 200% proof overlaps hero and Capture action")
    if geometry["focused_selector"] != ".oh__capture-card" or not geometry["focus_outline_visible"]:
        raise RuntimeError("Owner Home 200% proof lacks visible Capture focus")
    if any(
        not box or not box["visible"] or box["horizontally_clipped"]
        for box in geometry["essential_boxes"].values()
    ):
        raise RuntimeError(
            "Owner Home 200% proof clips or hides essential content: "
            + json.dumps(geometry["essential_boxes"], sort_keys=True)
        )
    return geometry


def main() -> None:
    if not CHROME:
        raise SystemExit(
            "Chrome is required (set PEERSLATE_CHROME, or install at a known "
            "Mac/Windows path)"
        )
    OUT.mkdir(parents=True, exist_ok=True)
    prior = {
        key: app.config.get(key)
        for key in (
            "TESTING",
            "PEERSLATE_OWNER_HOME_ENABLED",
            "PEERSLATE_ALLOW_DEV_IDENTITY",
            "PEERSLATE_DEV_USER_KEY",
        )
    }
    app.config.update(
        TESTING=True,
        PEERSLATE_OWNER_HOME_ENABLED=True,
        PEERSLATE_ALLOW_DEV_IDENTITY=True,
        PEERSLATE_DEV_USER_KEY="owner-home-evidence-owner",
    )
    provider = _Provider()
    captures = []

    with patch("auth_routes.owner_home_service", provider):
        server = make_server("127.0.0.1", 0, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=CHROME, headless=True)

                def capture(
                    name,
                    *,
                    mode="populated",
                    width=1440,
                    height=900,
                    reduced_motion=False,
                    forced_colors=False,
                    no_js=False,
                    action=None,
                    reflow=False,
                ):
                    provider.mode = mode
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        reduced_motion="reduce" if reduced_motion else "no-preference",
                        forced_colors="active" if forced_colors else "none",
                        java_script_enabled=not no_js,
                    )
                    page = context.new_page()
                    page.goto(f"{base_url}/app", wait_until="networkidle")
                    if action:
                        action(page)
                    page.wait_for_function(
                        "() => Array.from(document.images).every(image => image.complete)") if not no_js else None
                    geometry = {}
                    if reflow:
                        page.locator(".oh__capture-card").focus()
                        geometry["reflow"] = _assert_reflow_geometry(page)
                    target = OUT / name
                    page.screenshot(path=str(target), full_page=True, animations="disabled")
                    with Image.open(target) as image:
                        dimensions = f"{image.width}x{image.height}"
                    captures.append(
                        {
                            "file": name,
                            "state": name.removesuffix(".png"),
                            "viewport": f"{width}x{height}",
                            "dimensions": dimensions,
                            "theme": "dark",
                            "fixture_state": mode,
                            "java_script_enabled": not no_js,
                            "reduced_motion": reduced_motion,
                            "forced_colors": forced_colors,
                            "capture_method": "css-viewport-reflow-equivalent" if reflow else "native-css-viewport",
                            **(
                                {
                                    "browser_zoom_equivalent_percent": 200,
                                    "physical_viewport_equivalent": "1440x900",
                                }
                                if reflow
                                else {}
                            ),
                            **geometry,
                        }
                    )
                    context.close()

                capture("01-desktop-1440-populated.png")
                capture("02-mobile-390-populated.png", width=390, height=844)
                capture("03-mobile-320-populated.png", width=320, height=568)
                capture("04-landscape-844x400-populated.png", width=844, height=400)
                capture("05-200pct-zoom-reflow-720x450.png", width=720, height=450, reflow=True)
                capture(
                    "06-visible-focus-desktop.png",
                    action=lambda page: page.locator(".oh__capture-card").focus(),
                )
                capture("07-reduced-motion-desktop.png", reduced_motion=True)
                capture("08-forced-colors-desktop.png", forced_colors=True)
                capture("09-long-content-bidi-desktop.png", mode="long-bidi")
                capture("09b-long-content-bidi-mobile-390.png", mode="long-bidi", width=390, height=844)
                capture("10-empty-desktop.png", mode="empty")
                capture("10b-empty-mobile-390.png", mode="empty", width=390, height=844)
                capture("11-complete-failure-desktop.png", mode="failure")
                capture("11b-complete-failure-mobile-390.png", mode="failure", width=390, height=844)
                capture("12a-recovery-before-retry.png", mode="failure")

                def enhanced_retry(page):
                    provider.mode = "populated"
                    page.locator("[data-oh-retry]").click()
                    page.locator(".oh__stage-row--top").wait_for()

                capture("12b-recovery-after-retry.png", mode="failure", action=enhanced_retry)
                capture("13-no-js-populated-desktop.png", no_js=True)
                capture("13b-no-js-complete-failure-desktop.png", mode="failure", no_js=True)

                def native_retry(page):
                    provider.mode = "populated"
                    page.locator("[data-oh-retry]").click()
                    page.wait_for_load_state("networkidle")

                capture(
                    "13c-no-js-retry-link-worked-desktop.png",
                    mode="failure",
                    no_js=True,
                    action=native_retry,
                )
                capture("14a-two-owner-canary-priya-shah.png", mode="priya")
                capture("14b-two-owner-canary-noah-kim.png", mode="noah")
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            app.config.update(prior)

    (OUT / "capture-log.json").write_text(
        json.dumps(
            {
                "fixture": "process-local Mock-backed owner-home.v1; no database or SQL",
                "captures": captures,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
