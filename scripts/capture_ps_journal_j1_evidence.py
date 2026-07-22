"""Capture PS-JOURNAL-001 J1 evidence through the real Flask templates.

This is deliberately a local, TESTING-only utility. It never writes a Moment,
and the page fixture remains protected by the two server-side evidence guards.
The output is viewport-sized Chrome screenshots, not stitched or long-canvas
substitutes.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import app
from services.journal_service import JournalServiceError


OUT = ROOT / "artifacts" / "ps-journal-001-j1-frontend"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEV_USER_KEY = "journal-frontend-owner-1"
DETAIL_KEY = "e1111111-1111-1111-1111-111111111111"


def main() -> None:
    if not os.path.exists(CHROME):
        raise SystemExit(f"Chrome is required at {CHROME}")

    OUT.mkdir(parents=True, exist_ok=True)
    prior = {
        "TESTING": app.config.get("TESTING"),
        "PEERSLATE_JOURNAL_ENABLED": app.config.get("PEERSLATE_JOURNAL_ENABLED"),
        "PEERSLATE_JOURNAL_EVIDENCE_FIXTURES": app.config.get("PEERSLATE_JOURNAL_EVIDENCE_FIXTURES"),
        "PEERSLATE_JOURNAL_EVIDENCE_STATE": app.config.get("PEERSLATE_JOURNAL_EVIDENCE_STATE"),
        "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
        "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
    }
    app.config.update(
        TESTING=True,
        PEERSLATE_JOURNAL_ENABLED=True,
        PEERSLATE_JOURNAL_EVIDENCE_FIXTURES=True,
        PEERSLATE_JOURNAL_EVIDENCE_STATE="timeline",
        PEERSLATE_ALLOW_DEV_IDENTITY=True,
        PEERSLATE_DEV_USER_KEY=DEV_USER_KEY,
    )
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    captures: list[dict[str, object]] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROME, headless=True)

            def capture(
                name: str,
                state: str = "timeline",
                width: int = 1440,
                height: int = 1040,
                dark: bool = False,
                reduced_motion: bool = False,
                forced_colors: bool = False,
                path: str = "/app/journal",
                action=None,
            ) -> None:
                app.config["PEERSLATE_JOURNAL_EVIDENCE_FIXTURES"] = True
                app.config["PEERSLATE_JOURNAL_EVIDENCE_STATE"] = state
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    reduced_motion="reduce" if reduced_motion else "no-preference",
                    forced_colors="active" if forced_colors else "none",
                )
                if dark:
                    context.add_init_script("localStorage.setItem('ps-theme', 'dark');")
                page = context.new_page()
                page.goto(f"{base_url}{path}", wait_until="networkidle")
                page.evaluate("window.scrollTo(0, 0)")
                if action:
                    action(page)
                # Composer-only fixture media is initially in a hidden dialog;
                # wait for it to decode after that dialog opens so this remains
                # a faithful viewport capture rather than a race with image IO.
                page.wait_for_function(
                    """() => Array.from(document.images).every(
                        (image) => image.complete && image.naturalWidth > 0
                    )"""
                )
                geometry = {}
                if name == "timeline-desktop-light-1440.png":
                    geometry = page.evaluate(
                        """() => {
                            const box = (selector) => {
                                const node = document.querySelector(selector);
                                if (!node) return null;
                                const rect = node.getBoundingClientRect();
                                return { top: Math.round(rect.top), bottom: Math.round(rect.bottom) };
                            };
                            return {
                                hero: box('.ps-journal__hero'),
                                rail: {
                                    timeline: box('#journal-rail-timeline'),
                                    voice: box('#journal-rail-voice'),
                                    photos: box('#journal-rail-photos'),
                                    videos: box('#journal-rail-videos'),
                                    milestones: box('#journal-rail-milestones'),
                                    reflections: box('#journal-rail-reflections'),
                                    flourish: box('.ps-journal__rail-flourish-line'),
                                },
                                timeline: {
                                    may20: box('#journal-moment-e1111111-1111-1111-1111-111111111111'),
                                    may19: box('#journal-moment-e2222222-2222-2222-2222-222222222222'),
                                    may18: box('#journal-moment-e3333333-3333-3333-3333-333333333333'),
                                    may13: box('#journal-moment-e4444444-4444-4444-4444-444444444444'),
                                },
                            };
                        }"""
                    )
                if name == "detail-desktop-light-1440.png":
                    geometry = page.evaluate(
                        """() => {
                            const box = (selector) => {
                                const node = document.querySelector(selector);
                                if (!node) return null;
                                const rect = node.getBoundingClientRect();
                                return {
                                    left: Math.round(rect.left), top: Math.round(rect.top),
                                    width: Math.round(rect.width), height: Math.round(rect.height)
                                };
                            };
                            return {
                                detail: {
                                    title: box('.ps-moment__title'),
                                    context: box('.ps-moment__context'),
                                    audio: box('.ps-moment__voice-row'),
                                    photo: box('.ps-moment__photo'),
                                    date: box('.ps-moment__date'),
                                },
                            };
                        }"""
                    )
                if name == "empty-desktop-light-1440.png":
                    geometry = page.evaluate(
                        """() => {
                            const illustration = document.querySelector('.ps-journal__empty-illustration-svg');
                            const title = document.querySelector('.ps-journal__empty-title');
                            if (!illustration || !title) return { empty: null };
                            const rect = illustration.getBoundingClientRect();
                            const bounds = illustration.getBBox();
                            const viewBox = illustration.viewBox.baseVal;
                            const scale = rect.width / viewBox.width;
                            return {
                                empty: {
                                    illustration_width: Math.round(rect.width * 10) / 10,
                                    visual_gap: Math.round((title.getBoundingClientRect().top - (rect.top + (bounds.y + bounds.height) * scale)) * 10) / 10,
                                },
                            };
                        }"""
                    )
                page.screenshot(path=str(OUT / name), animations="disabled")
                captures.append(
                    {
                        "file": name,
                        "viewport": f"{width}x{height}",
                        "state": state,
                        "dark": dark,
                        "reduced_motion": reduced_motion,
                        "forced_colors": forced_colors,
                        "path": path,
                        **geometry,
                    }
                )
                context.close()

            capture("timeline-desktop-light-1440.png")
            capture("timeline-desktop-dark-1440.png", dark=True)
            capture("timeline-mobile-light-390.png", width=390, height=844)
            capture("timeline-mobile-dark-390.png", width=390, height=844, dark=True)
            capture("timeline-mobile-light-320.png", width=320, height=740)
            capture(
                "composer-type-desktop-light-1440.png",
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture(
                "composer-type-desktop-dark-1440.png",
                dark=True,
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture(
                "composer-speak-desktop-light-1440.png",
                action=lambda page: (
                    page.locator("#journal-open-composer").click(),
                    page.locator("[data-composer-tab='speak']").click(),
                ),
            )
            capture(
                "composer-speak-desktop-dark-1440.png",
                dark=True,
                action=lambda page: (
                    page.locator("#journal-open-composer").click(),
                    page.locator("[data-composer-tab='speak']").click(),
                ),
            )
            capture(
                "composer-type-mobile-light-390.png",
                width=390,
                height=844,
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture(
                "composer-type-mobile-dark-390.png",
                width=390,
                height=844,
                dark=True,
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture(
                "composer-speak-mobile-light-390.png",
                width=390,
                height=844,
                action=lambda page: (
                    page.locator("#journal-open-composer").click(),
                    page.locator("[data-composer-tab='speak']").click(),
                ),
            )
            capture(
                "composer-speak-mobile-dark-390.png",
                width=390,
                height=844,
                dark=True,
                action=lambda page: (
                    page.locator("#journal-open-composer").click(),
                    page.locator("[data-composer-tab='speak']").click(),
                ),
            )
            capture(
                "composer-type-mobile-light-320.png",
                width=320,
                height=740,
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture(
                "composer-type-mobile-dark-320.png",
                width=320,
                height=740,
                dark=True,
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture(
                "composer-speak-mobile-light-320.png",
                width=320,
                height=740,
                action=lambda page: (
                    page.locator("#journal-open-composer").click(),
                    page.locator("[data-composer-tab='speak']").click(),
                ),
            )
            capture(
                "composer-speak-mobile-dark-320.png",
                width=320,
                height=740,
                dark=True,
                action=lambda page: (
                    page.locator("#journal-open-composer").click(),
                    page.locator("[data-composer-tab='speak']").click(),
                ),
            )
            capture("saved-desktop-light-1440.png", state="saved")
            capture("saved-desktop-dark-1440.png", state="saved", dark=True)
            capture("saved-mobile-light-390.png", state="saved", width=390, height=844)
            capture("saved-mobile-dark-390.png", state="saved", width=390, height=844, dark=True)
            capture("empty-desktop-light-1440.png", state="empty")
            capture("empty-desktop-dark-1440.png", state="empty", dark=True)
            capture("empty-mobile-light-390.png", state="empty", width=390, height=844)
            capture("empty-mobile-dark-390.png", state="empty", width=390, height=844, dark=True)
            capture("manage-desktop-light-1440.png", state="manage")
            capture("manage-desktop-dark-1440.png", state="manage", dark=True)
            capture("manage-mobile-light-390.png", state="manage", width=390, height=844)
            capture("manage-mobile-dark-390.png", state="manage", width=390, height=844, dark=True)
            capture(
                "detail-desktop-light-1440.png",
                state="detail",
                path=f"/app/journal/moments/{DETAIL_KEY}",
            )
            capture(
                "detail-desktop-dark-1440.png",
                state="detail",
                dark=True,
                path=f"/app/journal/moments/{DETAIL_KEY}",
            )
            capture(
                "detail-mobile-light-390.png",
                state="detail",
                width=390,
                height=844,
                path=f"/app/journal/moments/{DETAIL_KEY}",
            )
            capture(
                "detail-mobile-dark-390.png",
                state="detail",
                width=390,
                height=844,
                dark=True,
                path=f"/app/journal/moments/{DETAIL_KEY}",
            )
            capture(
                "timeline-desktop-200pct-zoom-light-1440.png",
                action=lambda page: page.evaluate("document.body.style.zoom = '2'"),
            )
            capture(
                "composer-type-mobile-reduced-motion-390.png",
                width=390,
                height=844,
                reduced_motion=True,
                action=lambda page: page.locator("#journal-open-composer").click(),
            )
            capture("timeline-desktop-forced-colors-1440.png", forced_colors=True)

            def save_failure(page):
                def route(route):
                    route.fulfill(
                        status=503,
                        content_type="application/json",
                        json={"success": False, "error": "changed"},
                    )

                page.route("**/api/journal/moments**", route)
                page.locator("#journal-open-composer").click()
                page.locator("[data-composer-narrative]").fill(
                    "A private draft remains visible after a recoverable save failure."
                )
                page.locator("[data-composer-save]").click()
                page.wait_for_function(
                    "document.querySelector('[data-composer-status]').textContent.includes('did not save')"
                )

            capture(
                "composer-mobile-save-failure-390.png",
                width=390,
                height=844,
                action=save_failure,
            )
            capture(
                "composer-mobile-save-failure-dark-390.png",
                width=390,
                height=844,
                dark=True,
                action=save_failure,
            )
            capture(
                "composer-mobile-save-failure-light-320.png",
                width=320,
                height=740,
                action=save_failure,
            )
            capture(
                "composer-mobile-save-failure-dark-320.png",
                width=320,
                height=740,
                dark=True,
                action=save_failure,
            )

            def voice_failure(page):
                page.locator("#journal-open-composer").click()
                page.locator("[data-composer-tab='speak']").click()
                page.evaluate(
                    """() => Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
                        configurable: true,
                        value: async () => { throw new DOMException('Denied', 'NotAllowedError'); }
                    })"""
                )
                page.locator("[data-voice-action='start']").click()
                page.wait_for_function(
                    "document.querySelector('[data-voice-state-title]').textContent.includes('denied or unavailable')"
                )

            capture(
                "composer-mobile-voice-failure-390.png",
                width=390,
                height=844,
                action=voice_failure,
            )
            capture(
                "composer-mobile-voice-failure-dark-390.png",
                width=390,
                height=844,
                dark=True,
                action=voice_failure,
            )
            capture(
                "composer-mobile-voice-failure-light-320.png",
                width=320,
                height=740,
                action=voice_failure,
            )
            capture(
                "composer-mobile-voice-failure-dark-320.png",
                width=320,
                height=740,
                dark=True,
                action=voice_failure,
            )

            app.config["PEERSLATE_JOURNAL_EVIDENCE_FIXTURES"] = False
            with patch(
                "owner_routes.journal_service.list_owner_journal",
                side_effect=JournalServiceError("evidence unavailable"),
            ):
                context = browser.new_context(viewport={"width": 1440, "height": 1040})
                page = context.new_page()
                page.goto(f"{base_url}/app/journal", wait_until="networkidle")
                page.screenshot(path=str(OUT / "journal-unavailable-desktop-light-1440.png"))
                captures.append(
                    {
                        "file": "journal-unavailable-desktop-light-1440.png",
                        "viewport": "1440x1040",
                        "state": "service-unavailable",
                        "dark": False,
                        "reduced_motion": False,
                        "forced_colors": False,
                        "path": "/app/journal",
                    }
                )
                context.close()

            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        app.config.update(prior)

    (OUT / "capture-log.json").write_text(
        json.dumps({"fixture": "server-owned TESTING-only", "captures": captures}, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
