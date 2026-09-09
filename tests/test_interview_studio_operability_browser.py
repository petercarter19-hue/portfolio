"""Local browser proof for authenticated Interview Studio operability.

The suite uses an isolated test identity and the local Flask application only.
It never contacts live identity, provider, storage, or production services.
Optional screenshots and their manifest are written only to the external
directory named by ``PEERSLATE_INTERVIEW_EVIDENCE_DIR``.
"""

import base64
import hashlib
import json
import logging
import os
import subprocess
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
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


def _principal_header(subject="interview-operability-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Interview Operability Member"},
            {"typ": "email", "val": f"{subject}@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


def _mapped_user(*_args, **_kwargs):
    return {
        "account_key": "account-interview-operability-member",
        "user_key": "user-interview-operability-member",
        "display_name": "Interview Operability Member",
        "email": "interview-operability-member@example.com",
    }


def _review_payload():
    return {
        "verdict": "A clear answer with one useful next step.",
        "encouragement": "The action and outcome are easy to follow.",
        "whatCameThroughClearly": ["You owned the action."],
        "strengths": ["Specific action"],
        "improvements": ["Add the size of the result."],
        "strongerApproach": "Keep the structure and quantify the outcome.",
        "focusedFollowUp": "What changed because of your work?",
        "dimensions": [
            {
                "key": key,
                "status": "clear",
                "rationale": "Clear enough for this test.",
                "nextAction": "Add one verified detail.",
            }
            for key in (
                "situation_clarity",
                "action_ownership",
                "evidence",
                "outcome",
                "reflection",
            )
        ],
        "evidenceSuggestions": [],
    }


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for Interview Studio browser proof",
)
class InterviewStudioOperabilityBrowserTests(unittest.TestCase):
    """Exercise the real DOM, focus model, breakpoints, and no-JS fallback."""

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
        cls.identity_patch = patch("identity.database_service.first_row", side_effect=_mapped_user)
        cls.identity_patch.start()
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
        cls.evidence_dir = None
        evidence_value = os.environ.get("PEERSLATE_INTERVIEW_EVIDENCE_DIR", "").strip()
        if evidence_value:
            cls.evidence_dir = Path(evidence_value).expanduser().resolve()
            cls.evidence_dir.mkdir(parents=True, exist_ok=True)
        cls.capture_manifest = []
        cls.candidate_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).parents[1],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    @classmethod
    def tearDownClass(cls):
        if cls.evidence_dir is not None:
            manifest_path = cls.evidence_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "candidate_sha": cls.candidate_sha,
                        "fixture": "local-isolated-authenticated-member",
                        "captures": cls.capture_manifest,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
        cls.identity_patch.stop()
        cls.werkzeug_logger.setLevel(cls.werkzeug_log_level)
        limiter.enabled = cls.limiter_was_enabled
        app.config.update(cls.original_config)

    def _page(
        self,
        width=1440,
        height=900,
        java_script_enabled=True,
        forced_colors="none",
        reduced_motion="no-preference",
        path="/interview-studio",
    ):
        context = self.browser.new_context(
            viewport={"width": width, "height": height},
            java_script_enabled=java_script_enabled,
            forced_colors=forced_colors,
            reduced_motion=reduced_motion,
            extra_http_headers=_principal_header(),
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        page.goto(f"{self.base_url}{path}", wait_until="load")
        return page

    def _public_flag_off_page(self, width=390, height=844, java_script_enabled=False):
        context = self.browser.new_context(
            viewport={"width": width, "height": height},
            java_script_enabled=java_script_enabled,
        )
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        previous = app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"]
        app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = False
        try:
            page.goto(f"{self.base_url}/interview-studio", wait_until="load")
        finally:
            app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = previous
        return page

    def _capture(self, page, name, **metadata):
        if self.evidence_dir is None:
            return
        path = self.evidence_dir / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
        capture = {
            "name": name,
            "path": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "browser": self.browser.version,
            "candidate_sha": self.candidate_sha,
            "fixture": "local-isolated-authenticated-member",
        }
        capture.update(metadata)
        self.capture_manifest.append(capture)

    def _assert_no_horizontal_page_overflow(self, page):
        overflow = page.evaluate(
            """() => ({
                document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                body: document.body.scrollWidth - document.body.clientWidth,
            })"""
        )
        self.assertLessEqual(overflow["document"], 1, overflow)
        self.assertLessEqual(overflow["body"], 1, overflow)

    def test_single_controls_targets_and_reflow_at_supported_widths(self):
        for width, height, label in (
            (1440, 900, "desktop"),
            (768, 1024, "tablet"),
            (390, 844, "phone-390"),
            (320, 568, "phone-320"),
        ):
            with self.subTest(width=width):
                page = self._page(width, height)
                self.assertEqual(page.locator("h1").count(), 1)
                self.assertEqual(page.locator("[data-is-history-link]").count(), 1)
                self.assertEqual(page.locator("[data-is-session-setup-open]").count(), 1)
                self.assertEqual(page.locator("[data-is-settings-open]").count(), 1)
                for selector in (
                    "[data-is-history-link]",
                    "[data-is-session-setup-open]",
                    "[data-is-settings-open]",
                ):
                    box = page.locator(selector).bounding_box()
                    self.assertIsNotNone(box, selector)
                    self.assertGreaterEqual(box["height"], 44, (selector, box))
                    self.assertGreaterEqual(box["width"], 44, (selector, box))
                self._assert_no_horizontal_page_overflow(page)
                self._capture(
                    page,
                    f"authenticated-{label}",
                    viewport={"width": width, "height": height},
                    javascript=True,
                    forced_colors="none",
                    reduced_motion="no-preference",
                )

    def test_session_setup_keyboard_open_cancel_and_apply(self):
        page = self._page(390, 844)
        launcher = page.locator("[data-is-session-setup-open]")
        launcher.focus()
        launcher.press("Enter")
        page.wait_for_timeout(50)
        self.assertEqual(launcher.get_attribute("aria-expanded"), "true")
        self.assertFalse(page.locator("[data-is-session-setup]").get_attribute("hidden"))
        self.assertEqual(page.evaluate("document.activeElement.dataset.isSessionKind"), "")
        self.assertIn(
            "Use the defaults or adjust the context for your next question.",
            page.locator("[data-is-session-setup-consequence]").inner_text(),
        )
        self._capture(
            page,
            "session-setup-keyboard-focus",
            viewport={"width": 390, "height": 844},
            state="session-setup-open",
            focus="session-kind",
        )
        page.keyboard.press("Escape")
        page.wait_for_timeout(50)
        self.assertEqual(launcher.get_attribute("aria-expanded"), "false")
        self.assertTrue(page.locator("[data-is-session-setup]").get_attribute("hidden") is not None)
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-session-setup-open')"))

        launcher.press("Enter")
        page.locator("[data-is-start-session]").click()
        page.wait_for_timeout(50)
        self.assertEqual(launcher.get_attribute("aria-expanded"), "false")
        self.assertTrue(page.locator("[data-is-session-setup]").get_attribute("hidden") is not None)
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-answer')"))
        self.assertIn("setup applied", page.locator("[data-is-live]").inner_text().lower())

    def test_settings_focus_trap_escape_close_and_backdrop_return(self):
        page = self._page(768, 1024)
        launcher = page.locator("[data-is-settings-open]")
        launcher.focus()
        launcher.press("Enter")
        page.wait_for_timeout(50)
        dialog = page.locator("[data-is-settings]")
        self.assertTrue(dialog.evaluate("element => element.open"))
        self.assertEqual(launcher.get_attribute("aria-expanded"), "true")
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-confirm-navigation')"))
        self._capture(
            page,
            "studio-settings-keyboard-focus",
            viewport={"width": 768, "height": 1024},
            state="settings-open",
            focus="confirm-navigation",
        )

        page.locator("[data-is-clear-local]").focus()
        page.keyboard.press("Tab")
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-settings-close')"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(50)
        self.assertFalse(dialog.evaluate("element => element.open"))
        self.assertEqual(launcher.get_attribute("aria-expanded"), "false")
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-settings-open')"))

        launcher.press("Enter")
        dialog.evaluate("element => element.dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        page.wait_for_timeout(50)
        self.assertFalse(dialog.evaluate("element => element.open"))
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-settings-open')"))

        launcher.press("Enter")
        page.locator("[data-is-settings-close]").click()
        page.wait_for_timeout(50)
        self.assertFalse(dialog.evaluate("element => element.open"))
        self.assertTrue(page.evaluate("document.activeElement.hasAttribute('data-is-settings-open')"))

    def test_history_is_one_guarded_destination_and_persists_a_draft(self):
        page = self._page(1440, 900)
        answer = page.locator("[data-is-answer]")
        answer.fill("A draft that must remain local while History opens.")
        history = page.locator("[data-is-history-link]")
        self.assertEqual(history.get_attribute("href"), "/interview-studio/history")
        history.click()
        page.wait_for_url("**/interview-studio/history")
        self.assertEqual(page.locator("[data-is-history-link]").count(), 1)
        current_studio_destinations = page.locator(
            '[data-is-mode][aria-current="page"], [data-is-history-link][aria-current="page"]'
        )
        self.assertEqual(current_studio_destinations.count(), 1)
        self.assertEqual(current_studio_destinations.get_attribute("data-is-history-link"), "")
        stored = page.evaluate(
            """() => Object.keys(localStorage)
                .filter(key => key.includes(':draft:'))
                .map(key => localStorage.getItem(key))"""
        )
        self.assertTrue(
            any("A draft that must remain local while History opens." in item for item in stored),
            stored,
        )

    def test_review_and_unsaved_improvement_survive_modes_history_and_refresh(self):
        page = self._page(1440, 900)
        review = _review_payload()
        page.route(
            "**/api/interview/review",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"review": review}),
            ),
        )
        page.route(
            "**/api/interview/improve",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "improvement": {
                            "draft": "I led the recovery and restored service within one hour.",
                            "changes": ["Added a concrete result"],
                            "confirmations": [],
                            "evidenceUsed": [],
                        }
                    }
                ),
            ),
        )

        page.locator("[data-is-answer]").fill(
            "I led a recovery, coordinated the team, and restored service."
        )
        page.locator("[data-is-review]").click()
        page.locator(".is-stack__coaching").first.wait_for(state="visible")
        self.assertIn("A clear answer", page.locator(".is-stack__coaching").first.inner_text())

        page.locator('[data-is-mode="ai"]').click()
        page.locator('[data-is-mode="me"]').click()
        self.assertTrue(page.locator(".is-stack__coaching").first.is_visible())

        page.locator("[data-is-history-link]").click()
        page.wait_for_url("**/interview-studio/history")
        self.assertEqual(page.locator(".is-history__row").count(), 1)
        page.locator('[data-is-mode="me"]').click()
        self.assertTrue(page.locator(".is-stack__coaching").first.is_visible())

        page.get_by_role("button", name="Improve My Answer").click()
        improved = page.locator('textarea[aria-label="Editable improved draft"]')
        improved.wait_for(state="visible")
        improved.fill("I led the recovery and restored service in 47 minutes.")
        page.locator('[data-is-mode="video"]').click()
        page.locator('[data-is-mode="me"]').click()
        self.assertEqual(improved.input_value(), "I led the recovery and restored service in 47 minutes.")

        page.reload(wait_until="load")
        restored = page.locator('textarea[aria-label="Editable improved draft"]')
        restored.wait_for(state="visible")
        self.assertEqual(restored.input_value(), "I led the recovery and restored service in 47 minutes.")
        self.assertIn("not yet in History", page.locator(".is-stack__draft-label").inner_text())
        page.locator("[data-is-history-link]").click()
        page.wait_for_url("**/interview-studio/history")
        self.assertEqual(page.locator(".is-history__row").count(), 1)
        page.locator('[data-is-mode="me"]').click()
        page.get_by_role("button", name="Keep original answer").click()
        page.get_by_role("button", name="Edit and retry").click()
        answer = page.locator("[data-is-answer]")
        self.assertTrue(answer.is_visible())
        self.assertTrue(answer.is_editable())
        self.assertEqual(
            answer.input_value(),
            "I led a recovery, coordinated the team, and restored service.",
        )
        page.locator("[data-is-history-link]").click()
        page.wait_for_url("**/interview-studio/history")
        self.assertEqual(page.locator(".is-history__row").count(), 1)

        page.locator('[data-is-mode="me"]').click()
        page.reload(wait_until="load")
        answer = page.locator("[data-is-answer]")
        self.assertEqual(
            answer.input_value(),
            "I led a recovery, coordinated the team, and restored service.",
        )
        page.locator("[data-is-review]").click()
        page.locator(".is-stack__coaching").first.wait_for(state="visible")
        page.locator("[data-is-history-link]").click()
        page.wait_for_url("**/interview-studio/history")
        self.assertEqual(page.locator(".is-history__row").count(), 2)
        attempt_numbers = page.evaluate(
            """() => {
                const key = Object.keys(localStorage).find((item) => item.endsWith(':history'));
                return JSON.parse(localStorage.getItem(key)).map((record) => record.attemptNumber);
            }"""
        )
        self.assertEqual(attempt_numbers, [2, 1])

        page.evaluate("window.confirm = () => true")
        page.locator(".is-history__row-delete").first.click()
        self.assertEqual(page.locator(".is-history__row").count(), 1)
        active_residue = page.evaluate(
            """() => Object.keys(localStorage).filter(
                (key) => key.endsWith(':active-review') || key.includes(':draft:')
            )"""
        )
        self.assertEqual(active_residue, [])
        page.reload(wait_until="load")
        page.locator('[data-is-mode="me"]').click()
        self.assertEqual(page.locator("[data-is-answer]").input_value(), "")

    def test_storage_failures_keep_review_actions_visible_and_truthful(self):
        page = self._page(1440, 900)
        page.route(
            "**/api/interview/review",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"review": _review_payload()}),
            ),
        )
        page.route(
            "**/api/interview/improve",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "improvement": {
                            "draft": "A stronger browser-local draft.",
                            "changes": ["Added a concrete result"],
                            "confirmations": [],
                            "evidenceUsed": [],
                        }
                    }
                ),
            ),
        )
        page.locator("[data-is-answer]").fill("A reviewed answer that must remain visible.")
        page.locator("[data-is-review]").click()
        page.locator(".is-stack__coaching").first.wait_for(state="visible")
        page.get_by_role("button", name="Improve My Answer").click()
        improvement = page.locator(".is-stack__improve")
        improvement.wait_for(state="visible")

        page.evaluate(
            """() => {
                Storage.prototype.__practiceSetItem = Storage.prototype.setItem;
                Storage.prototype.setItem = () => { throw new Error('storage unavailable'); };
            }"""
        )
        page.get_by_role("button", name="Keep original answer").click()
        self.assertTrue(improvement.is_visible())
        page.wait_for_function(
            "document.querySelector('[data-is-live]').textContent.includes('could not be cleared')"
        )
        page.evaluate(
            """() => {
                Storage.prototype.setItem = Storage.prototype.__practiceSetItem;
                delete Storage.prototype.__practiceSetItem;
            }"""
        )
        page.evaluate(
            """() => {
                Storage.prototype.__practiceRemoveItem = Storage.prototype.removeItem;
                Storage.prototype.removeItem = () => { throw new Error('storage unavailable'); };
            }"""
        )
        page.get_by_role("button", name="Edit and retry").click()
        self.assertTrue(page.locator(".is-stack__coaching").first.is_visible())
        page.wait_for_function(
            "document.querySelector('[data-is-live]').textContent.includes('could not start')"
        )
        page.evaluate(
            """() => {
                Storage.prototype.removeItem = Storage.prototype.__practiceRemoveItem;
                delete Storage.prototype.__practiceRemoveItem;
            }"""
        )
        page.locator("[data-is-history-link]").click()
        page.wait_for_url("**/interview-studio/history")
        self.assertEqual(page.locator(".is-history__row").count(), 1)
        page.evaluate(
            """() => {
                window.confirm = () => true;
                Storage.prototype.__practiceGetItem = Storage.prototype.getItem;
                Storage.prototype.getItem = () => { throw new Error('storage unreadable'); };
            }"""
        )
        page.locator(".is-history__row-delete").click()
        self.assertEqual(page.locator(".is-history__row").count(), 1)
        page.wait_for_function(
            "document.querySelector('[data-is-live]').textContent.includes('could not be deleted')"
        )
        page.evaluate(
            """() => {
                Storage.prototype.getItem = Storage.prototype.__practiceGetItem;
                delete Storage.prototype.__practiceGetItem;
            }"""
        )
        preserved_records = page.evaluate(
            """() => {
                const key = Object.keys(localStorage).find((item) => item.endsWith(':history'));
                return key ? JSON.parse(localStorage.getItem(key)) : [];
            }"""
        )
        self.assertEqual(len(preserved_records), 1)
        active_workspace = page.evaluate(
            """() => {
                const key = Object.keys(localStorage).find((item) => item.endsWith(':active-review'));
                return key ? JSON.parse(localStorage.getItem(key)) : null;
            }"""
        )
        self.assertEqual(active_workspace["improvement"]["draft"], "A stronger browser-local draft.")
        page.evaluate(
            """() => {
                window.confirm = () => true;
                Storage.prototype.__practiceRemoveItem = Storage.prototype.removeItem;
                Storage.prototype.removeItem = () => { throw new Error('storage unavailable'); };
            }"""
        )
        page.locator(".is-history__row-delete").click()
        self.assertEqual(page.locator(".is-history__row").count(), 1)
        active_workspace = page.evaluate(
            """() => {
                const key = Object.keys(localStorage).find((item) => item.endsWith(':active-review'));
                return key ? JSON.parse(localStorage.getItem(key)) : null;
            }"""
        )
        self.assertEqual(active_workspace["improvement"]["draft"], "A stronger browser-local draft.")
        page.wait_for_function(
            "document.querySelector('[data-is-live]').textContent.includes('could not be deleted')"
        )
        page.evaluate(
            """() => {
                Storage.prototype.removeItem = Storage.prototype.__practiceRemoveItem;
                delete Storage.prototype.__practiceRemoveItem;
            }"""
        )

    def test_authenticated_flow_omits_finish_and_keeps_setup_dismissible(self):
        page = self._page(390, 844)
        self.assertEqual(page.locator("[data-is-finish-session]").count(), 0)
        self.assertEqual(page.locator("[data-is-panel=complete]").count(), 0)
        launcher = page.locator("[data-is-session-setup-open]")
        launcher.click()
        page.keyboard.press("Escape")
        self.assertTrue(page.locator("[data-is-session-setup]").get_attribute("hidden") is not None)
        page.wait_for_function("document.activeElement.hasAttribute('data-is-session-setup-open')")

    def test_video_history_guard_refusal_preserves_the_local_transcript(self):
        page = self._page(390, 844, path="/interview-studio?mode=video")
        transcript = page.locator("[data-is-video-transcript]")
        transcript.fill("A local transcript that must not be discarded.")
        page.evaluate("window.confirm = () => false")
        page.locator("[data-is-history-link]").click()
        page.wait_for_timeout(50)
        self.assertTrue(page.url.endswith("/interview-studio?mode=video"), page.url)
        self.assertEqual(transcript.input_value(), "A local transcript that must not be discarded.")

        page.evaluate("window.confirm = () => true")
        page.locator("[data-is-history-link]").click()
        page.wait_for_url("**/interview-studio/history")

    def test_no_javascript_keeps_real_links_and_hides_js_only_launchers(self):
        page = self._page(320, 568, java_script_enabled=False)
        self.assertEqual(page.locator("h1").count(), 1)
        self.assertTrue(page.locator("[data-is-history-link]").is_visible())
        self.assertEqual(page.locator("[data-is-mode]").count(), 3)
        self.assertTrue(page.locator('[data-is-mode="ai"]').is_visible())
        self.assertFalse(page.locator("[data-is-mode-toggle]").is_visible())
        self.assertFalse(page.locator("[data-is-session-setup-open]").is_visible())
        self.assertFalse(page.locator("[data-is-settings-open]").is_visible())
        self._assert_no_horizontal_page_overflow(page)
        self._capture(
            page,
            "authenticated-no-javascript",
            viewport={"width": 320, "height": 568},
            javascript=False,
        )
        page.locator('[data-is-mode="ai"]').click()
        page.wait_for_url("**/interview-studio?mode=ai")
        self.assertEqual(page.locator('[data-is-mode="ai"]').get_attribute("aria-current"), "page")
        self.assertIsNone(page.locator('[data-is-mode="ai"]').get_attribute("aria-selected"))

        history_page = self._page(
            320,
            568,
            path="/interview-studio/history",
            java_script_enabled=False,
        )
        current_studio_destinations = history_page.locator(
            '[data-is-mode][aria-current="page"], [data-is-history-link][aria-current="page"]'
        )
        self.assertEqual(current_studio_destinations.count(), 1)
        self.assertEqual(
            current_studio_destinations.get_attribute("data-is-history-link"),
            "",
        )

    def test_public_flag_off_composition_does_not_receive_member_launchers(self):
        page = self._public_flag_off_page()
        self.assertFalse(page.locator("[data-interview-studio]").evaluate("element => element.hasAttribute('data-authenticated')"))
        self.assertEqual(page.locator("[data-is-settings-open]").count(), 0)
        self.assertEqual(page.locator("[data-is-session-setup-open]").count(), 0)
        self.assertEqual(page.locator("[data-is-mode]").count(), 3)
        self.assertTrue(page.locator("[data-is-history-link]").is_visible())
        self._assert_no_horizontal_page_overflow(page)
        self._capture(
            page,
            "public-flag-off-no-javascript",
            viewport={"width": 390, "height": 844},
            javascript=False,
            fixture="public-flag-off",
        )

    def test_text_spacing_forced_colors_and_reduced_motion_remain_operable(self):
        spacing_page = self._page(320, 568)
        spacing_page.add_style_tag(
            content="*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}"
        )
        self._assert_no_horizontal_page_overflow(spacing_page)
        self._capture(
            spacing_page,
            "authenticated-text-spacing-400-percent-reflow",
            viewport={"width": 320, "height": 568},
            effective_zoom="400-percent-width-equivalent",
            text_spacing=True,
        )

        forced_page = self._page(390, 844, forced_colors="active")
        forced_page.locator("[data-is-settings-open]").focus()
        outline = forced_page.locator("[data-is-settings-open]").evaluate(
            "element => getComputedStyle(element).outlineStyle"
        )
        self.assertNotEqual(outline, "none")
        self._assert_no_horizontal_page_overflow(forced_page)
        self._capture(
            forced_page,
            "authenticated-forced-colors",
            viewport={"width": 390, "height": 844},
            forced_colors="active",
        )

        reduced_page = self._page(640, 900, reduced_motion="reduce")
        transition_seconds = reduced_page.locator("[data-is-mode-toggle]").evaluate(
            """element => {
                const value = getComputedStyle(element.querySelector('.is-auth__mode-toggle-caret')).transitionDuration;
                return value.endsWith('ms') ? parseFloat(value) / 1000 : parseFloat(value);
            }"""
        )
        self.assertLessEqual(transition_seconds, 0.001)
        self._assert_no_horizontal_page_overflow(reduced_page)
        self._capture(
            reduced_page,
            "authenticated-reduced-motion-200-percent-reflow",
            viewport={"width": 640, "height": 900},
            effective_zoom="200-percent-width-equivalent",
            reduced_motion="reduce",
        )


if __name__ == "__main__":
    unittest.main()
