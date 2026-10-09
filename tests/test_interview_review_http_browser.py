"""One local browser Review click that reaches Flask with a stubbed provider.

This is not the intercepted operability suite. Playwright must not fulfill
``/api/interview/review``. The Flask route is exercised in-process with
``app.client.messages.create`` stubbed. Ordinary unittest discovery may skip
when Playwright or Chrome is absent; the dedicated runner fails closed on skip.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import threading
import unittest
from unittest.mock import Mock, patch

from werkzeug.serving import make_server

import identity
import app as app_module
from app import INTERVIEW_FAMILY_DIMENSIONS, app, limiter

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
    "HTTP-contract fixture: I named the disagreement, owned the follow-up, "
    "and recorded the outcome."
)
UNIQUE_VERDICT = "Flask reached this review"
BEHAVIORAL_DIMENSIONS = INTERVIEW_FAMILY_DIMENSIONS["behavioral"]
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
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_FakeContentBlock(text)]
        self.stop_reason = stop_reason


def _principal_header(subject="interview-review-http-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Interview Review HTTP Member"},
            {"typ": "email", "val": f"{subject}@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


def _mapped_user(*_args, **_kwargs):
    return {
        "account_key": "account-interview-review-http-member",
        "user_key": "user-interview-review-http-member",
        "display_name": "Interview Review HTTP Member",
        "email": "interview-review-http-member@example.com",
    }


def _review_payload():
    return {
        "verdict": UNIQUE_VERDICT,
        "encouragement": "The local Flask route returned this stubbed review.",
        "whatCameThroughClearly": ["You named a concrete disagreement."],
        "strengths": ["Clear ownership of the follow-up."],
        "improvements": ["Add one observable result."],
        "strongerApproach": "Open with the disagreement, the action you owned, and the result.",
        "focusedFollowUp": "What changed after the conversation?",
        "dimensions": [
            {
                "key": key,
                "status": "clear",
                "rationale": "Present in this fixture answer.",
                "nextAction": "Keep the same structure.",
            }
            for key in BEHAVIORAL_DIMENSIONS
        ],
        "evidenceSuggestions": [],
    }


def snapshot_review_http_runtime():
    """Capture process-global Interview test fixtures for isolation checks."""
    return {
        "config": {key: app.config.get(key) for key in _CONFIG_KEYS},
        "limiter_enabled": limiter.enabled,
        "werkzeug_level": logging.getLogger("werkzeug").level,
    }


def _restore_review_http_runtime(snapshot):
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


def install_review_http_runtime_fixtures(cls):
    """Install isolated Flask/identity/provider fixtures with class cleanups.

    Each resource is registered with ``addClassCleanup`` immediately after it is
    acquired so a later ``setUpClass`` failure still restores state. unittest
    runs class cleanups in reverse order and continues after a cleanup error.
    Restore of application configuration is registered first so it runs last.
    """
    snapshot = {
        "config": {key: app.config.get(key) for key in _CONFIG_KEYS},
        "limiter_enabled": limiter.enabled,
        "werkzeug_level": logging.getLogger("werkzeug").level,
    }
    cls.addClassCleanup(_restore_review_http_runtime, snapshot)

    cls.provider_calls = []
    cls.identity_calls = []

    def mapped_user(*args, **kwargs):
        cls.identity_calls.append((args, kwargs))
        return _mapped_user(*args, **kwargs)

    def fake_messages_create(**kwargs):
        cls.provider_calls.append(kwargs)
        return _FakeProviderResponse(json.dumps(_review_payload()))

    app.config.update(
        TESTING=True,
        PEERSLATE_ALLOW_DEV_IDENTITY=False,
        PEERSLATE_DEV_USER_KEY=None,
        PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
        PEERSLATE_AUTH_ISSUER=None,
        PEERSLATE_AUTH_PROVIDER_NAME="aad",
        PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED=True,
        PEERSLATE_OWNER_USER_KEYS="",
        PEERSLATE_OWNER_EMAILS="",
    )
    limiter.enabled = False

    identity_patch = patch(
        "identity.database_service.first_row",
        side_effect=mapped_user,
    )
    identity_patch.start()
    cls.addClassCleanup(_stop_started_patch, identity_patch)
    cls.identity_patch = identity_patch

    provider_patch = patch(
        "app.client.messages.create",
        side_effect=fake_messages_create,
    )
    provider_patch.start()
    cls.addClassCleanup(_stop_started_patch, provider_patch)
    cls.provider_patch = provider_patch

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    cls.addClassCleanup(_shutdown_local_server, server, thread)
    thread.start()
    cls.server = server
    cls.server_thread = thread
    cls.base_url = f"http://127.0.0.1:{server.server_port}"


def start_review_http_browser(cls, playwright_factory=None, chrome_executable=None):
    """Start Playwright and Chromium, registering each cleanup before the next step."""
    factory = sync_playwright if playwright_factory is None else playwright_factory
    executable = CHROME_EXECUTABLE if chrome_executable is None else chrome_executable
    playwright_runtime = factory().start()
    cls.addClassCleanup(_stop_playwright, playwright_runtime)
    cls.playwright = playwright_runtime
    browser = playwright_runtime.chromium.launch(
        executable_path=executable,
        headless=True,
    )
    cls.addClassCleanup(_close_browser, browser)
    cls.browser = browser


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for Interview Review HTTP proof",
)
class InterviewReviewHttpBrowserTests(unittest.TestCase):
    """Browser -> Flask /api/interview/review with an in-process provider stub."""

    @classmethod
    def setUpClass(cls):
        install_review_http_runtime_fixtures(cls)
        start_review_http_browser(cls)

    def test_review_click_reaches_flask_with_stubbed_provider(self):
        context = self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            extra_http_headers=_principal_header(),
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())

        review_requests = []
        review_statuses = []

        def capture_request(request):
            if request.method == "POST" and request.url.split("?", 1)[0].endswith(
                "/api/interview/review"
            ):
                review_requests.append(request.url)

        def capture_response(response):
            request = response.request
            if request.method == "POST" and request.url.split("?", 1)[0].endswith(
                "/api/interview/review"
            ):
                review_statuses.append(response.status)

        page.on("request", capture_request)
        page.on("response", capture_response)
        page.goto(f"{self.base_url}/interview-studio", wait_until="load")

        question = page.locator("[data-is-question]").inner_text().strip()
        self.assertTrue(question)
        page.locator("[data-is-answer]").fill(KNOWN_ANSWER)
        self.provider_calls.clear()
        page.locator("[data-is-review]").click()
        page.locator(".is-stack__coaching", has_text=UNIQUE_VERDICT).wait_for(
            state="visible",
            timeout=15000,
        )

        self.assertTrue(review_requests, "browser never posted /api/interview/review")
        for url in review_requests:
            self.assertTrue(
                url.startswith(self.base_url + "/api/interview/review"),
                url,
            )
        self.assertEqual(review_statuses, [200])
        self.assertEqual(len(self.provider_calls), 1)
        user_content = self.provider_calls[0]["messages"][0]["content"]
        self.assertIn(question, user_content)
        self.assertIn(KNOWN_ANSWER, user_content)
        self.assertTrue(self.identity_calls)
        self.assertIn(
            UNIQUE_VERDICT,
            page.locator(".is-stack__coaching").first.inner_text(),
        )
        self.assertIn(
            UNIQUE_VERDICT,
            page.locator("[data-is-verdict]").text_content() or "",
        )


class InterviewReviewHttpBrowserCleanupTests(unittest.TestCase):
    """Prove partial class setup cannot leak Interview application fixtures."""

    def test_chromium_launch_failure_restores_runtime_fixtures(self):
        before = snapshot_review_http_runtime()
        playwright_stopped = []

        class FakePlaywright:
            def start(self):
                runtime = Mock()
                runtime.stop.side_effect = lambda: playwright_stopped.append("stop")
                runtime.chromium.launch.side_effect = RuntimeError(
                    "synthetic Chromium launch failure"
                )
                return runtime

        class Probe(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                install_review_http_runtime_fixtures(cls)
                start_review_http_browser(cls, playwright_factory=FakePlaywright)

            def test_unreachable(self):
                raise AssertionError("setUpClass must fail before the test body")

        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Probe)
        )
        error_text = " ".join(
            str(item) for pair in result.errors for item in pair[1:]
        )
        self.assertIn("synthetic Chromium launch failure", error_text)
        self.assertEqual(playwright_stopped, ["stop"])
        after = snapshot_review_http_runtime()
        self.assertEqual(after["config"], before["config"])
        self.assertEqual(after["limiter_enabled"], before["limiter_enabled"])
        self.assertEqual(after["werkzeug_level"], before["werkzeug_level"])
        self.assertNotIsInstance(identity.database_service.first_row, Mock)
        self.assertNotIsInstance(app_module.client.messages.create, Mock)

    def test_remaining_class_cleanups_run_after_one_failure(self):
        ran = []

        class Probe(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                cls.addClassCleanup(ran.append, "restore_config")

                def boom():
                    ran.append("boom")
                    raise RuntimeError("synthetic cleanup failure")

                cls.addClassCleanup(boom)
                cls.addClassCleanup(ran.append, "close_browser")

            def test_ok(self):
                return

        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Probe)
        )
        error_text = " ".join(str(item) for pair in result.errors for item in pair[1:])
        self.assertIn("synthetic cleanup failure", error_text)
        self.assertEqual(ran, ["close_browser", "boom", "restore_config"])


if __name__ == "__main__":
    unittest.main()
