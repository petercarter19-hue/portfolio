"""Real browser -> Flask -> service journeys for the MVP1 C composer.

Playwright drives a real headless Chrome against a locally served Flask app.
The parser and transcription seams are in-process deterministic stubs that
record the exact bytes they received, so the browser evidence is real
(page -> event -> request -> view -> service -> seam -> response -> DOM) while
the provider boundary stays synthetic. The application's own HTTP responses are
never intercepted.

Ordinary unittest discovery may skip when Playwright or Chrome is unavailable.
This is not SQL engine proof, live identity proof or live provider proof.
"""

from __future__ import annotations

import logging
import json
import os
import re
import tempfile
import threading
import unittest

from werkzeug.serving import make_server

from app import app, limiter
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_guide_service import ResumeGuideService, GuideUnavailableError
from services.resume_intake_document_adapter import ResumeDocumentAdapter
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService
from services.resume_intake_service import ResumeIntakeUnavailableError
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - environment capability gate
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - optional local browser helper
    CHROME_EXECUTABLE = None


CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_RESUME_EDITOR_ENABLED",
    "PEERSLATE_RESUME_INTAKE_ENABLED",
    "PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED",
    "RESUME_DRAFT_SERVICE",
    "RESUME_INTAKE_SERVICE",
    "RESUME_GUIDE_SERVICE",
)

TRANSCRIPT = "Browser journey transcript: I led a cross-team migration."


class _RecordingTranscriber:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({"bytes": audio_bytes, "content_type": content_type})
        return {
            "provider_transcript": TRANSCRIPT,
            "provider_request_id": "browser-stub-1",
            "duration_seconds": 2.0,
        }


def _stop_patch(patcher):
    try:
        patcher.stop()
    except RuntimeError:
        return


def _shutdown_server(server, thread):
    try:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
    finally:
        server.server_close()


def _close_browser(browser):
    browser.close()


def _stop_playwright(runtime):
    runtime.stop()


def _remove_file(path):
    try:
        os.remove(path)
    except OSError:
        return


def install_intake_runtime_fixtures(cls):
    """Install isolated Flask/service fixtures, registering cleanup on acquire."""

    snapshot = {
        "config": {key: app.config.get(key) for key in CONFIG_KEYS},
        "limiter_enabled": limiter.enabled,
        "werkzeug_level": logging.getLogger("werkzeug").level,
    }

    def restore():
        app.config.update(snapshot["config"])
        limiter.enabled = snapshot["limiter_enabled"]
        logging.getLogger("werkzeug").setLevel(snapshot["werkzeug_level"])

    cls.addClassCleanup(restore)

    cls.catalog = InMemoryCanonicalCatalog()
    cls.draft_service = ResumeDraftService(
        repository=InMemoryResumeDraftRepository(), catalog=cls.catalog
    )
    cls.repository = InMemoryResumeIntakeRepository()
    cls.transcriber = _RecordingTranscriber()
    cls.received_documents = []

    def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
        cls.received_documents.append({"content_type": content_type, "data": admitted})
        from services.my_opportunities.member_import_service import ImportStageOutcome

        return (
            "Uploaded resume text: Systems Engineer who supports requirements management.",
            "extracted", None, False,
            (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                outcome="extracted", reason_code=None, occurred_at=now),),
        )

    cls.intake_service = ResumeIntakeService(
        repository=cls.repository,
        draft_service=cls.draft_service,
        document_adapter=ResumeDocumentAdapter(),
        transcription_adapter=ResumeTranscriptionAdapter(service=cls.transcriber),
        policy=selected_policy_for_tests(),
        document_pipeline=pipeline,
    )
    app.config.update(
        TESTING=True,
        PEERSLATE_ALLOW_DEV_IDENTITY=True,
        PEERSLATE_DEV_USER_KEY="intake-browser-member",
        PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
        PEERSLATE_RESUME_EDITOR_ENABLED=True,
        PEERSLATE_RESUME_INTAKE_ENABLED=True,
        PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=True,
        RESUME_DRAFT_SERVICE=cls.draft_service,
        RESUME_INTAKE_SERVICE=cls.intake_service,
        RESUME_GUIDE_SERVICE=ResumeGuideService(repository=cls.repository),
    )
    limiter.enabled = False
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    cls.addClassCleanup(_shutdown_server, server, thread)
    thread.start()
    cls.server = server
    cls.server_thread = thread
    cls.base_url = f"http://127.0.0.1:{server.server_port}"


def start_browser(cls):
    runtime = sync_playwright().start()
    cls.addClassCleanup(_stop_playwright, runtime)
    cls.playwright = runtime
    browser = runtime.chromium.launch(
        executable_path=CHROME_EXECUTABLE,
        headless=True,
        args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
    )
    cls.addClassCleanup(_close_browser, browser)
    cls.browser = browser


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for the composer browser proof",
)
class ResumeIntakeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_intake_runtime_fixtures(cls)
        start_browser(cls)
        handle, cls.document_path = tempfile.mkstemp(suffix=".txt")
        os.close(handle)
        with open(cls.document_path, "w", encoding="utf-8") as stream:
            stream.write("Systems Engineer at Northrop Grumman")
        cls.addClassCleanup(_remove_file, cls.document_path)

    def _new_page(self, **context_kwargs):
        context = self.browser.new_context(**context_kwargs)
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        return page

    def _use_owner(self, name):
        app.config["PEERSLATE_DEV_USER_KEY"] = name
        self.addCleanup(app.config.update, {"PEERSLATE_DEV_USER_KEY": "intake-browser-member"})
        return name

    def test_mixed_add_reaches_flask_and_reports_a_truthful_receipt(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        self.assertTrue(page.locator("#resume-intake").is_visible())

        typed = "One project I worked on involved a cross-team migration."
        page.locator("#resume-intake-text").fill(typed)

        # One structured fact, queued by the member and saved by explicit Add.
        page.locator("#resume-intake-type").select_option("skill")
        page.locator("#resume-intake-skill").fill("Requirements management")
        page.locator("#resume-intake-add-fact").click()
        self.assertIn("Requirements management", page.locator("#resume-intake-queued").inner_text())

        # A real synthetic document upload through the browser's own file input.
        self.received_documents.clear()
        page.locator("#resume-intake-file").set_input_files(self.document_path)
        attachment_text = page.locator("#resume-intake-attachments").inner_text().lower()
        self.assertIn(".txt", attachment_text)
        self.assertIn("not added yet", attachment_text)

        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-receipt").get_by_text("saved privately").first.wait_for(timeout=15000)

        receipt = page.locator("#resume-intake-receipt").inner_text()
        self.assertIn("1 saved privately", receipt)
        self.assertIn("2 needs your review", receipt)

        # The server really received the uploaded bytes through the seam.
        self.assertEqual(len(self.received_documents), 1)
        self.assertEqual(
            self.received_documents[0]["data"], b"Systems Engineer at Northrop Grumman"
        )
        self.assertEqual(self.received_documents[0]["content_type"], "text/plain")

        # The explicit fact is private; the free text is only a pending proposal.
        saved = self.catalog.list_items("intake-browser-member")
        self.assertEqual(len(saved), 1)
        self.assertFalse(saved[0]["resume_display"])
        self.assertFalse(saved[0]["visitor_ai"])
        # The unfinished follow-up is visible as a pending proposal, not saved.
        page.locator("#resume-intake-proposals").get_by_text(
            "cross-team migration", exact=False
        ).first.wait_for(timeout=10000)

        # A refresh recovers the confirmed durable state from the server. The
        # unsent follow-up text is honestly not promised to survive, so the
        # receipt (not the raw draft) is what returns.
        page.reload(wait_until="load")
        page.locator("#resume-intake-receipt").get_by_text(
            "1 saved privately", exact=False
        ).first.wait_for(timeout=15000)

    def test_guide_hide_reopen_preserves_unfinished_text(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        unfinished = "Half-written answer I have not added yet."
        page.locator("#resume-intake-text").fill(unfinished)
        page.locator("#resume-intake-hide").click()
        self.assertFalse(page.locator("#resume-intake-guide").is_visible())
        self.assertTrue(page.locator("#resume-intake-reopen").is_visible())
        page.locator("#resume-intake-reopen").click()
        self.assertTrue(page.locator("#resume-intake-guide").is_visible())
        self.assertEqual(page.locator("#resume-intake-text").input_value(), unfinished)
        self.assertIn("Not added yet", page.locator("#resume-intake-draft-label").inner_text())

    def test_in_field_microphone_inserts_without_overwriting_typing(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        typed = "Typed before recording."
        page.locator("#resume-intake-text").fill(typed)

        page.locator("#resume-intake-mic").click()
        page.wait_for_timeout(1500)
        page.locator("#resume-intake-mic").click()

        # Wait for the transcript to land (or an honest refusal), then check the
        # typed text survived the late transcription either way.
        try:
            page.wait_for_function(
                "() => (document.getElementById('resume-intake-text').value || '').indexOf('Browser journey transcript') !== -1"
                " || /not supported|permission|did not|could not/i.test("
                "document.getElementById('resume-intake-status').textContent || '')",
                timeout=20000,
            )
        except Exception:  # pragma: no cover - timing only
            pass
        value = page.locator("#resume-intake-text").input_value()
        self.assertIn(typed, value)
        if TRANSCRIPT in value:
            self.assertGreaterEqual(len(self.transcriber.calls), 1)
            self.assertTrue(self.transcriber.calls[0]["bytes"])
            self.assertIn("Recording", page.locator("#resume-intake-attachments").inner_text())
        else:
            status = page.locator("#resume-intake-status").inner_text().lower()
            self.assertTrue(
                "microphone" in status or "recording" in status,
                f"expected an honest microphone state, saw {status!r}",
            )

    def test_mobile_composition_reflows_without_horizontal_overflow(self):
        page = self._new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        self.assertTrue(page.locator("#resume-intake").is_visible())
        self.assertTrue(page.locator("#resume-intake-text").is_visible())
        self.assertTrue(page.locator("#resume-intake-add").is_visible())
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        self.assertLessEqual(overflow, 1, "the composer must not cause horizontal overflow at 390px")

    def test_mixed_saved_failed_and_review_items_clear_only_acknowledged_inputs(self):
        owner = self._use_owner("browser-mixed")
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        typed = "Follow-up wording that becomes a pending proposal."
        page.locator("#resume-intake-text").fill(typed)
        page.locator("#resume-intake-type").select_option("skill")
        page.locator("#resume-intake-skill").fill("Requirements management")
        page.locator("#resume-intake-add-fact").click()
        # A file the server refuses (unsupported declared type), added through
        # the browser's own file input.
        bad = os.path.join(tempfile.gettempdir(), "intake-bad.zip")
        with open(bad, "wb") as stream:
            stream.write(b"PK\x03\x04not-a-real-document")
        self.addCleanup(_remove_file, bad)
        page.locator("#resume-intake-file").set_input_files(bad)
        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-receipt").get_by_text("1 saved privately", exact=False).first.wait_for(
            timeout=15000
        )
        receipt = page.locator("#resume-intake-receipt").inner_text()
        self.assertIn("1 saved privately", receipt)
        self.assertIn("1 needs your review", receipt)
        self.assertIn("1 could not be saved", receipt)
        # The acknowledged text was cleared; the refused file is still unsent
        # and the saved fact is no longer queued.
        self.assertEqual(
            page.evaluate("() => document.getElementById('resume-intake-text').value"), ""
        )
        attachments = page.locator("#resume-intake-attachments").inner_text().lower()
        self.assertIn("still unsent", attachments)
        self.assertEqual(page.locator("#resume-intake-queued").inner_text().strip(), "")
        saved = self.catalog.list_items(owner)
        self.assertEqual(len(saved), 1)
        self.assertFalse(saved[0]["resume_display"])

    def test_newer_typing_during_a_slow_add_is_never_discarded(self):
        self._use_owner("browser-newer-typing")
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-text").fill("First version of my answer.")
        # Type again after the click but before the response renders.
        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-text").fill("First version of my answer. And a newer sentence.")
        page.locator("#resume-intake-receipt").get_by_text("needs your review", exact=False).first.wait_for(
            timeout=15000
        )
        self.assertIn(
            "newer sentence", page.locator("#resume-intake-text").input_value()
        )

    def test_lost_response_retries_the_same_request_without_duplicates(self):
        owner = self._use_owner("browser-lost-response")
        original = app.config["RESUME_INTAKE_SERVICE"]
        lost = {"used": False}

        class LostOnceService(ResumeIntakeService):
            def submit(self, owner_key, payload, **kwargs):
                result = super().submit(owner_key, payload, **kwargs)
                if not lost["used"]:
                    lost["used"] = True
                    # The write committed; the response never reached the client.
                    raise ResumeIntakeUnavailableError(proposed={"text": payload.get("text")})
                return result

        app.config["RESUME_INTAKE_SERVICE"] = LostOnceService(
            repository=self.repository,
            draft_service=self.draft_service,
            policy=selected_policy_for_tests(),
        )
        self.addCleanup(app.config.update, {"RESUME_INTAKE_SERVICE": original})

        page = self._new_page(viewport={"width": 1440, "height": 1000})
        request_ids = []

        def capture(request):
            if request.method == "POST" and request.url.endswith("/api/resume-intake/me/submissions"):
                body = request.post_data or ""
                marker = '"request_id":"'
                if marker in body:
                    request_ids.append(body.split(marker, 1)[1].split('"', 1)[0])

        page.on("request", capture)
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-text").fill("Recover me after a dropped response.")
        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-status").get_by_text("unsent", exact=False).wait_for(timeout=15000)
        # The client keeps the same request and every byte for the retry.
        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-receipt").get_by_text("needs your review", exact=False).first.wait_for(
            timeout=15000
        )
        self.assertEqual(len(request_ids), 2)
        self.assertEqual(request_ids[0], request_ids[1])
        self.assertEqual(len(self.repository.load_owner(owner)["submissions"]), 1)

    def test_mobile_sheet_dismiss_and_reopen_preserves_queued_and_attached_input(self):
        self._use_owner("browser-sheet")
        page = self._new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        typed = "Unsaved mobile answer."
        page.locator("#resume-intake-text").fill(typed)
        page.locator("#resume-intake-type").select_option("skill")
        page.locator("#resume-intake-skill").fill("MBSE")
        page.locator("#resume-intake-add-fact").click()
        page.locator("#resume-intake-file").set_input_files(self.document_path)
        # Dismiss the sheet.
        page.locator("#resume-intake-hide").click()
        self.assertFalse(page.locator("#resume-intake").is_visible())
        self.assertTrue(page.locator("#resume-intake-reopen").is_visible())
        # Reopen using the floating chip.
        page.locator("#resume-intake-reopen").click()
        self.assertTrue(page.locator("#resume-intake").is_visible())
        self.assertEqual(page.locator("#resume-intake-text").input_value(), typed)
        self.assertIn("MBSE", page.locator("#resume-intake-queued").inner_text())
        self.assertIn(".txt", page.locator("#resume-intake-attachments").inner_text().lower())

    def test_proposal_list_renders_empty_few_and_many(self):
        self._use_owner("browser-proposals")
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-proposals").get_by_text("Nothing is waiting").wait_for(timeout=15000)
        for index in range(3):
            page.locator("#resume-intake-text").fill(f"Review item number {index}.")
            page.locator("#resume-intake-add").click()
            page.locator("#resume-intake-status").get_by_text("review", exact=False).wait_for(timeout=15000)
        page.locator("#resume-intake-proposals").locator("li").nth(2).wait_for(timeout=15000)
        self.assertGreaterEqual(page.locator("#resume-intake-proposals").locator("li").count(), 3)

    def test_two_hundred_percent_reflow_has_no_horizontal_overflow(self):
        self._use_owner("browser-zoom")
        # 200% of a 1440x900 desktop viewport is ~720x450 CSS pixels.
        page = self._new_page(viewport={"width": 720, "height": 450})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-text").fill("Zoomed reflow check.")
        overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        self.assertLessEqual(overflow, 1, "200% zoom must not cause horizontal overflow")
        self.assertTrue(page.locator("#resume-intake-add").is_visible())

    def test_clear_affordance_never_offers_a_required_field(self):
        self._use_owner("browser-clears")
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-type").select_option("role")
        clears = page.locator("#resume-intake-clears")
        text = clears.inner_text()
        # Required subject fields are absent; optional fields are offered.
        self.assertNotIn("role title", text)
        self.assertNotIn("employer", text)
        self.assertIn("summary", text)
        page.locator("#resume-intake-type").select_option("skill")
        self.assertIn("summary", page.locator("#resume-intake-clears").inner_text())
        self.assertNotIn("name", page.locator("#resume-intake-clears").inner_text().split("summary")[0])

    def test_lost_recording_response_retries_with_the_same_request_and_content(self):
        self._use_owner("browser-recording-retry")
        original = app.config["RESUME_INTAKE_SERVICE"]
        lost = {"used": False}

        class LostOnceRecording(ResumeIntakeService):
            def transcribe_recording(self, owner_key, upload, payload, **kwargs):
                result = super().transcribe_recording(owner_key, upload, payload, **kwargs)
                if not lost["used"]:
                    lost["used"] = True
                    raise ResumeIntakeUnavailableError(proposed={"client_key": payload.get("client_key")})
                return result

        app.config["RESUME_INTAKE_SERVICE"] = LostOnceRecording(
            repository=self.repository,
            draft_service=self.draft_service,
            transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber),
            policy=selected_policy_for_tests(),
        )
        self.addCleanup(app.config.update, {"RESUME_INTAKE_SERVICE": original})
        provider_calls = len(self.transcriber.calls)

        page = self._new_page(viewport={"width": 1440, "height": 1000})
        request_payloads = []

        def capture(request):
            if request.method == "POST" and request.url.endswith("/api/resume-intake/me/recordings"):
                raw = request.post_data_buffer or b""
                body = raw.decode("utf-8", "replace")
                match = re.search(r"\r\n\r\n(\{[^\r\n]+\})\r\n", body)
                if match:
                    request_payloads.append(json.loads(match.group(1)))

        page.on("request", capture)
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-mic").click()
        page.wait_for_timeout(1500)
        page.locator("#resume-intake-mic").click()
        # The first response is lost; the client keeps the same request and
        # offers to retry the SAME audio.
        page.locator("#resume-intake-status").get_by_text("unsent", exact=False).wait_for(timeout=20000)
        self.assertEqual(
            page.evaluate("() => document.getElementById('resume-intake-text').value"), ""
        )
        # A normal member delay must not change duration or any other digest
        # input before Try again retransmits the original recording request.
        page.wait_for_timeout(2500)
        page.locator("#resume-intake-attachments").get_by_text("Try again", exact=True).click()
        page.wait_for_function(
            "() => (document.getElementById('resume-intake-text').value || '').indexOf('Browser journey transcript') !== -1",
            timeout=25000,
        )
        self.assertEqual(len(request_payloads), 2)
        self.assertEqual(request_payloads[0], request_payloads[1])
        # One provider call for the original transcription, none for the replay.
        self.assertEqual(len(self.transcriber.calls), provider_calls + 1)

    def test_earlier_recording_retry_keeps_its_request_after_a_second_recording(self):
        self._use_owner("browser-recording-intervening")
        original = app.config["RESUME_INTAKE_SERVICE"]
        lost = {"used": False}

        class LostFirstRecording(ResumeIntakeService):
            def transcribe_recording(self, owner_key, upload, payload, **kwargs):
                result = super().transcribe_recording(owner_key, upload, payload, **kwargs)
                if not lost["used"]:
                    lost["used"] = True
                    raise ResumeIntakeUnavailableError(
                        proposed={"client_key": payload.get("client_key")}
                    )
                return result

        app.config["RESUME_INTAKE_SERVICE"] = LostFirstRecording(
            repository=self.repository,
            draft_service=self.draft_service,
            transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber),
            policy=selected_policy_for_tests(),
        )
        self.addCleanup(app.config.update, {"RESUME_INTAKE_SERVICE": original})
        provider_calls = len(self.transcriber.calls)
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        request_payloads = []

        def capture(request):
            if request.method == "POST" and request.url.endswith("/api/resume-intake/me/recordings"):
                body = (request.post_data_buffer or b"").decode("utf-8", "replace")
                match = re.search(r"\r\n\r\n(\{[^\r\n]+\})\r\n", body)
                if match:
                    request_payloads.append(json.loads(match.group(1)))

        page.on("request", capture)
        page.goto(f"{self.base_url}/app/resume", wait_until="load")

        page.locator("#resume-intake-mic").click()
        page.wait_for_timeout(1200)
        page.locator("#resume-intake-mic").click()
        page.locator("#resume-intake-status").get_by_text("unsent", exact=False).wait_for(
            timeout=20000
        )

        # A second, independent recording succeeds before the first row is retried.
        page.locator("#resume-intake-mic").click()
        page.wait_for_timeout(2200)
        page.locator("#resume-intake-mic").click()
        page.wait_for_function("() => document.querySelectorAll('#resume-intake-attachments li').length === 2")
        page.wait_for_function(
            "() => (document.getElementById('resume-intake-text').value.match(/Browser journey transcript/g) || []).length === 1",
            timeout=20000,
        )

        page.locator("#resume-intake-attachments").get_by_text("Try again", exact=True).click()
        page.wait_for_function(
            "() => (document.getElementById('resume-intake-text').value.match(/Browser journey transcript/g) || []).length === 2",
            timeout=20000,
        )

        self.assertEqual(len(request_payloads), 3)
        self.assertEqual(request_payloads[0], request_payloads[2])
        self.assertNotEqual(request_payloads[0]["request_id"], request_payloads[1]["request_id"])
        self.assertNotEqual(request_payloads[0]["client_key"], request_payloads[1]["client_key"])
        self.assertNotEqual(
            request_payloads[0]["duration_seconds"], request_payloads[1]["duration_seconds"]
        )
        self.assertEqual(len(self.transcriber.calls), provider_calls + 2)

    def test_lost_guide_response_retries_with_the_same_request(self):
        self._use_owner("browser-guide-retry")
        original = app.config["RESUME_GUIDE_SERVICE"]
        lost = {"used": False}

        class LostOnceGuide(ResumeGuideService):
            def set_status(self, owner_key, payload, **kwargs):
                result = super().set_status(owner_key, payload, **kwargs)
                if not lost["used"]:
                    lost["used"] = True
                    raise GuideUnavailableError("synthetic lost response")
                return result

        app.config["RESUME_GUIDE_SERVICE"] = LostOnceGuide(repository=self.repository)
        self.addCleanup(app.config.update, {"RESUME_GUIDE_SERVICE": original})
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        request_payloads = []

        def capture(request):
            if request.method == "POST" and request.url.endswith("/api/resume-intake/me/guide/status"):
                request_payloads.append(request.post_data_json)

        page.on("request", capture)
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        page.locator("#resume-intake-complete").click()
        page.locator("#resume-intake-status").get_by_text("unavailable", exact=False).wait_for(
            timeout=15000
        )
        page.locator("#resume-intake-complete").click()
        page.locator("#resume-intake-reopen").wait_for(state="visible", timeout=15000)

        self.assertEqual(len(request_payloads), 2)
        self.assertEqual(request_payloads[0], request_payloads[1])

    def test_education_and_credential_add_and_proposal_accept_use_member_status_choices(self):
        owner = self._use_owner("browser-status-matrix")
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")

        page.locator("#resume-intake-type").select_option("education")
        page.locator("#resume-intake-education-title").fill("Systems Engineering")
        page.locator("#resume-intake-institution").fill("Example University")
        page.locator("#resume-intake-education-status").select_option("completed")
        page.locator("#resume-intake-add-fact").click()

        page.locator("#resume-intake-type").select_option("credential")
        page.locator("#resume-intake-credential").fill("Architecture Certificate")
        page.locator("#resume-intake-issuer").fill("Example Institute")
        page.locator("#resume-intake-credential-status").select_option("completed")
        page.locator("#resume-intake-credential-issue-date").fill("2026-09-01")
        page.locator("#resume-intake-add-fact").click()
        page.locator("#resume-intake-add").click()
        page.wait_for_function(
            "() => (document.getElementById('resume-intake-receipt').textContent || '').indexOf('2 saved privately') !== -1",
            timeout=15000,
        )

        def accept_typed(record_type, wording, detail_selector, detail_value, status_selector):
            page.locator("#resume-intake-text").fill("Proposal source for " + record_type)
            page.locator("#resume-intake-add").click()
            proposal = page.locator("#resume-intake-proposals > li").first
            proposal.locator("[data-proposal-type]").wait_for(timeout=15000)
            proposal.locator("[data-proposal-type]").select_option(record_type)
            proposal.locator("[data-proposal-wording]").fill(wording)
            proposal.locator(detail_selector).fill(detail_value)
            proposal.locator(status_selector).select_option("in_progress")
            proposal.get_by_text("Save this privately", exact=True).click()
            page.locator("#resume-intake-proposals").get_by_text(
                "Nothing is waiting", exact=False
            ).wait_for(timeout=15000)

        accept_typed(
            "education", "Applied Systems Program", "[data-proposal-institution]",
            "Example College", "[data-proposal-education-status]",
        )
        accept_typed(
            "credential", "Safety Credential", "[data-proposal-issuer]",
            "Example Board", "[data-proposal-credential-status]",
        )

        records = self.catalog.list_items(owner)
        self.assertEqual(sum(row["record_type"] == "education" for row in records), 2)
        self.assertEqual(sum(row["record_type"] == "credential" for row in records), 2)

    def test_impact_requires_an_owner_parent(self):
        self._use_owner("browser-parent")
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/resume", wait_until="load")
        # Seed one role so a parent exists.
        page.locator("#resume-intake-type").select_option("role")
        page.locator("#resume-intake-role-title").fill("Engineering Manager")
        page.locator("#resume-intake-employer").fill("Northrop Grumman")
        page.locator("#resume-intake-add-fact").click()
        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-receipt").get_by_text("saved privately", exact=False).first.wait_for(timeout=15000)

        page.locator("#resume-intake-type").select_option("accomplishment")
        page.locator("#resume-intake-wording").fill("Led the platform migration")
        # Without a parent the composer refuses to queue the Impact.
        page.locator("#resume-intake-add-fact").click()
        self.assertIn("Choose which entry", page.locator("#resume-intake-status").inner_text())
        self.assertEqual(page.locator("#resume-intake-queued").inner_text().strip(), "")
        # The member's own entry is offered as the parent.
        page.wait_for_function(
            "() => document.querySelectorAll('#resume-intake-parent option').length > 1",
            timeout=15000,
        )
        page.locator("#resume-intake-parent").select_option(index=1)
        page.locator("#resume-intake-add-fact").click()
        self.assertIn("Led the platform migration", page.locator("#resume-intake-queued").inner_text())
        page.locator("#resume-intake-add").click()
        page.locator("#resume-intake-receipt").get_by_text("saved privately", exact=False).first.wait_for(timeout=15000)


if __name__ == "__main__":
    unittest.main()
