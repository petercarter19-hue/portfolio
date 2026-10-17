"""Fail-closed browser proof for Interview Studio F2/F3 repairs.

Playwright must not fulfill ``/api/interview/review``. The Flask route is
exercised in-process with ``app.client.messages.create`` stubbed. Ordinary
unittest discovery may skip when Playwright or Chrome is absent; the dedicated
runner fails closed on skip.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
import unittest
from unittest.mock import patch

from werkzeug.serving import make_server

from app import app, limiter

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - environment capability gate
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - optional local browser helper
    CHROME_EXECUTABLE = None


KNOWN_ANSWER = (
    "unreadable-review-please Audit fixture: I named the disagreement, "
    "owned the follow-up, and recorded the outcome in writing."
)
_CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_AUTH_ISSUER",
    "PEERSLATE_AUTH_PROVIDER_NAME",
    "PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED",
    "PEERSLATE_OWNER_USER_KEYS",
    "PEERSLATE_OWNER_EMAILS",
)


class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeProviderResponse:
    def __init__(self, text):
        self.content = [_FakeContentBlock(text)]
        self.stop_reason = "end_turn"


def _principal_header(subject="interview-recovery-mobile-nav-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Interview Recovery Member"},
            {"typ": "email", "val": f"{subject}@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("ascii")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


def _mapped_user(*_args, **_kwargs):
    return {
        "account_key": "account-interview-recovery-mobile-nav",
        "user_key": "user-interview-recovery-mobile-nav",
        "display_name": "Interview Recovery Member",
        "email": "interview-recovery-mobile-nav@example.com",
    }


def _restore_runtime(snapshot):
    app.config.update(snapshot["config"])
    limiter.enabled = snapshot["limiter_enabled"]
    logging.getLogger("werkzeug").setLevel(snapshot["werkzeug_level"])


def _stop_started_patch(patcher):
    try:
        patcher.stop()
    except RuntimeError:
        return


def _shutdown_local_server(server, thread):
    try:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
    finally:
        server.server_close()


def _close_browser(browser):
    browser.close()


def _stop_playwright(playwright_runtime):
    playwright_runtime.stop()


def _control(page, selector):
    locator = page.locator(selector).first
    if locator.count() == 0:
        return {"present": False, "visible": False, "enabled": False}
    return {
        "present": True,
        "visible": locator.is_visible(),
        "enabled": locator.is_enabled(),
        "hidden": locator.get_attribute("hidden") is not None,
        "aria_hidden": locator.get_attribute("aria-hidden"),
        "tabindex": locator.get_attribute("tabindex"),
    }


def _studio_history(page):
    return page.evaluate(
        """() => {
            const key = Object.keys(localStorage).find((item) => item.endsWith(':history'));
            return key ? JSON.parse(localStorage.getItem(key) || '[]') : [];
        }"""
    )


def _wait_until(predicate, timeout=4.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _is_review_post(request):
    return request.method == "POST" and request.url.split("?", 1)[0].endswith(
        "/api/interview/review"
    )


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for Interview recovery/mobile-nav proof",
)
class InterviewRecoveryMobileNavBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot = {
            "config": {key: app.config.get(key) for key in _CONFIG_KEYS},
            "limiter_enabled": limiter.enabled,
            "werkzeug_level": logging.getLogger("werkzeug").level,
        }
        cls.addClassCleanup(_restore_runtime, snapshot)

        cls.provider_calls = []
        cls.provider_gate = threading.Event()
        cls.provider_gate.set()
        cls.hang_provider = False

        def fake_messages_create(**kwargs):
            cls.provider_calls.append(kwargs)
            if cls.hang_provider:
                cls.provider_gate.wait(timeout=8)
            return _FakeProviderResponse("this is not json at all")

        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_AUTH_ISSUER=None,
            PEERSLATE_AUTH_PROVIDER_NAME="aad",
            PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED=False,
            PEERSLATE_OWNER_USER_KEYS="",
            PEERSLATE_OWNER_EMAILS="",
        )
        limiter.enabled = False

        identity_patch = patch(
            "identity.database_service.first_row",
            side_effect=_mapped_user,
        )
        identity_patch.start()
        cls.addClassCleanup(_stop_started_patch, identity_patch)

        provider_patch = patch(
            "app.client.messages.create",
            side_effect=fake_messages_create,
        )
        provider_patch.start()
        cls.addClassCleanup(_stop_started_patch, provider_patch)

        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        cls.addClassCleanup(_shutdown_local_server, server, thread)
        thread.start()
        cls.server = server
        cls.base_url = f"http://127.0.0.1:{server.server_port}"

        playwright_runtime = sync_playwright().start()
        cls.addClassCleanup(_stop_playwright, playwright_runtime)
        browser = playwright_runtime.chromium.launch(
            executable_path=CHROME_EXECUTABLE,
            headless=True,
        )
        cls.addClassCleanup(_close_browser, browser)
        cls.browser = browser

    def setUp(self):
        self.provider_calls.clear()
        type(self).hang_provider = False
        self.provider_gate.set()
        app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = False

    def _page(self, width=1440, height=900, authenticated=False, **context_kwargs):
        headers = _principal_header() if authenticated else None
        context = self.browser.new_context(
            viewport={"width": width, "height": height},
            extra_http_headers=headers,
            **context_kwargs,
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        posts = []

        def capture(request):
            if _is_review_post(request):
                posts.append(request.post_data or "")

        page.on("request", capture)
        page.posts = posts
        if authenticated:
            app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = True
        page.goto(f"{self.base_url}/interview-studio", wait_until="load")
        starter = page.locator("[data-is-start-session]")
        if starter.count() and starter.first.is_visible():
            starter.first.click()
        page.locator("[data-is-answer]").wait_for()
        return page

    def _fail_coaching(self, page):
        page.locator("[data-is-answer]").fill(KNOWN_ANSWER)
        page.locator("[data-is-review]").click()
        page.locator("[data-is-review-error]:not([hidden])").wait_for(timeout=15000)
        page.locator("[data-is-retry-coaching]:not([hidden])").wait_for()

    def test_unreadable_provider_preserves_answer_and_one_recovery_control(self):
        page = self._page()
        self._fail_coaching(page)
        self.assertEqual(page.locator("[data-is-answer]").input_value(), KNOWN_ANSWER)
        review = _control(page, "[data-is-review]")
        retry = _control(page, "[data-is-retry-coaching]")
        self.assertTrue(retry["visible"])
        self.assertTrue(retry["enabled"])
        self.assertFalse(review["visible"] and review["enabled"])
        self.assertTrue(review["hidden"] or review["aria_hidden"] == "true")
        self.assertGreaterEqual(len(page.posts), 1)
        history = page.evaluate(
            """() => {
                const key = Object.keys(localStorage).find((item) => item.endsWith(':history'));
                return key ? JSON.parse(localStorage.getItem(key) || '[]') : [];
            }"""
        )
        self.assertEqual(history, [])

    def test_keep_editing_makes_no_request_and_restores_review(self):
        page = self._page()
        self._fail_coaching(page)
        before = len(page.posts)
        page.locator("[data-is-keep-editing]").click()
        page.wait_for_timeout(200)
        self.assertEqual(len(page.posts), before)
        self.assertEqual(page.locator("[data-is-answer]").input_value(), KNOWN_ANSWER)
        self.assertTrue(page.locator("[data-is-review-error]").get_attribute("hidden") is not None)
        review = _control(page, "[data-is-review]")
        self.assertTrue(review["visible"])
        self.assertTrue(review["enabled"])
        self.assertTrue(
            page.evaluate("document.activeElement.hasAttribute('data-is-answer')")
        )

    def test_one_retry_activation_posts_once_without_duplicate_history(self):
        page = self._page()
        self._fail_coaching(page)
        before = len(page.posts)
        page.locator("[data-is-retry-coaching]").click()
        page.locator("[data-is-review-error]:not([hidden])").wait_for(timeout=15000)
        self.assertGreater(len(page.posts), before)
        # One Retry click may still use the existing 5xx automatic retry,
        # but it must not create a second user-facing submission path or History.
        self.assertLessEqual(len(page.posts) - before, 2)
        history = page.evaluate(
            """() => {
                const key = Object.keys(localStorage).find((item) => item.endsWith(':history'));
                return key ? JSON.parse(localStorage.getItem(key) || '[]') : [];
            }"""
        )
        self.assertEqual(history, [])
        self.assertEqual(page.locator("[data-is-answer]").input_value(), KNOWN_ANSWER)
        review = _control(page, "[data-is-review]")
        self.assertFalse(review["visible"] and review["enabled"])

    def test_pending_retry_ignores_duplicate_activation(self):
        page = self._page()
        self._fail_coaching(page)
        type(self).hang_provider = True
        self.provider_gate.clear()
        posts_before = len(page.posts)
        provider_before = len(self.provider_calls)
        try:
            with page.expect_request(_is_review_post, timeout=4000):
                page.evaluate(
                    "document.querySelector('[data-is-retry-coaching]').click()"
                )
            reached_provider = _wait_until(
                lambda: len(self.provider_calls) - provider_before >= 1
            )
            self.assertTrue(
                reached_provider,
                "first Retry did not reach the blocked provider",
            )
            self.assertEqual(
                len(page.posts) - posts_before,
                1,
                "first Retry must issue exactly one browser POST before the automatic 5xx retry",
            )
            page.evaluate("document.querySelector('[data-is-retry-coaching]').click()")
            for _ in range(8):
                page.wait_for_timeout(50)
                self.assertEqual(
                    len(page.posts) - posts_before,
                    1,
                    "duplicate Retry queued a second browser POST while the first request was pending",
                )
        finally:
            self.provider_gate.set()
            type(self).hang_provider = False
        page.locator("[data-is-review-error]:not([hidden])").wait_for(timeout=15000)
        for _ in range(8):
            page.wait_for_timeout(50)
            self.assertLessEqual(
                len(page.posts) - posts_before,
                2,
                "Retry activation issued more browser POSTs than the existing automatic 5xx retry allows",
            )
        self.assertGreaterEqual(len(page.posts) - posts_before, 1)
        self.assertLessEqual(len(page.posts) - posts_before, 2)
        self.assertEqual(_studio_history(page), [])
        self.assertEqual(page.locator("[data-is-answer]").input_value(), KNOWN_ANSWER)
        review = _control(page, "[data-is-review]")
        retry = _control(page, "[data-is-retry-coaching]")
        self.assertFalse(review["visible"] and review["enabled"])
        self.assertTrue(retry["visible"])
        self.assertTrue(retry["enabled"])

    def test_mobile_menu_hides_interview_dock_at_390_and_320(self):
        for width, height in ((390, 844), (320, 800)):
            with self.subTest(width=width):
                page = self._page(width, height)
                dock = page.locator(".is__composer-actions")
                self.assertTrue(dock.is_visible())
                page.locator("[data-platform-menu-toggle]").click()
                page.wait_for_timeout(150)
                self.assertIn(
                    "has-platform-menu-open",
                    page.evaluate("document.body.className"),
                )
                self.assertFalse(dock.is_visible())
                self.assertFalse(page.locator('[data-is-mic="answer"]').first.is_visible())
                overflow = page.evaluate(
                    """() => document.documentElement.scrollWidth - document.documentElement.clientWidth"""
                )
                self.assertLessEqual(overflow, 1)

    def test_menu_escape_returns_to_opener_and_keyboard_departure_closes_without_stealing_focus(self):
        page = self._page(390, 844)
        opener = page.locator("[data-platform-menu-toggle]")
        opener.click()
        page.wait_for_timeout(100)
        self.assertTrue(
            page.evaluate(
                "document.activeElement.closest('[data-platform-menu]') !== null"
            )
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)
        self.assertTrue(
            page.evaluate(
                "document.activeElement.hasAttribute('data-platform-menu-toggle')"
            )
        )
        self.assertTrue(
            page.locator("[data-platform-menu]").get_attribute("hidden") is not None
        )

        opener.click()
        page.wait_for_timeout(100)
        sign_in = page.get_by_role("link", name="Sign in", exact=True)
        sign_in.focus()
        page.wait_for_timeout(100)
        self.assertTrue(
            page.locator("[data-platform-menu]").get_attribute("hidden") is not None
        )
        self.assertTrue(
            page.evaluate(
                """() => {
                    const el = document.activeElement;
                    return Boolean(el && (el.textContent || '').includes('Sign in'));
                }"""
            )
        )

    def test_public_and_authenticated_recovery_remain_distinct(self):
        public = self._page()
        self._fail_coaching(public)
        self.assertIn(
            "Coaching could not be completed.",
            public.locator("[data-is-review-error]").inner_text(),
        )
        self.assertEqual(
            public.locator("[data-is-retry-coaching]").inner_text().strip()[:14],
            "Retry coaching",
        )

        app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = True
        authenticated = self._page(authenticated=True)
        self._fail_coaching(authenticated)
        self.assertIn(
            "We couldn't review this answer right now.",
            authenticated.locator("[data-is-review-error]").inner_text(),
        )
        self.assertIn(
            "Try review again",
            authenticated.locator("[data-is-retry-coaching]").inner_text(),
        )
        review = _control(authenticated, "[data-is-review]")
        self.assertFalse(review["visible"] and review["enabled"])


if __name__ == "__main__":
    unittest.main()
