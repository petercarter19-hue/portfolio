"""One local browser Review click that reaches Flask with a stubbed provider.

This is not the intercepted operability suite. Playwright must not fulfill
``/api/interview/review``. The Flask route is exercised in-process with
``app.client.messages.create`` stubbed. Ordinary unittest discovery may skip
when Playwright or Chrome is absent; the dedicated runner fails closed on skip.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import unittest
from unittest.mock import patch

from werkzeug.serving import make_server

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


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for Interview Review HTTP proof",
)
class InterviewReviewHttpBrowserTests(unittest.TestCase):
    """Browser -> Flask /api/interview/review with an in-process provider stub."""

    @classmethod
    def setUpClass(cls):
        cls.original_config = {
            key: app.config.get(key)
            for key in (
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
        }
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
        cls.limiter_was_enabled = limiter.enabled
        limiter.enabled = False
        cls.provider_calls = []
        cls.identity_calls = []

        def mapped_user(*args, **kwargs):
            cls.identity_calls.append((args, kwargs))
            return _mapped_user(*args, **kwargs)

        def fake_messages_create(**kwargs):
            cls.provider_calls.append(kwargs)
            return _FakeProviderResponse(json.dumps(_review_payload()))

        cls.identity_patch = patch(
            "identity.database_service.first_row",
            side_effect=mapped_user,
        )
        cls.provider_patch = patch(
            "app.client.messages.create",
            side_effect=fake_messages_create,
        )
        cls.identity_patch.start()
        cls.provider_patch.start()
        cls.werkzeug_logger = logging.getLogger("werkzeug")
        cls.werkzeug_log_level = cls.werkzeug_logger.level
        cls.werkzeug_logger.setLevel(logging.ERROR)
        cls.server = make_server("127.0.0.1", 0, app)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=CHROME_EXECUTABLE,
            headless=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
        cls.provider_patch.stop()
        cls.identity_patch.stop()
        cls.werkzeug_logger.setLevel(cls.werkzeug_log_level)
        limiter.enabled = cls.limiter_was_enabled
        app.config.update(cls.original_config)

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


if __name__ == "__main__":
    unittest.main()
