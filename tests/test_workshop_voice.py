"""Contract tests for Workshop voice input — PS-WORKSHOP-001 W2d.

Controlling authority: docs/initiatives/PS-SLATE-STUDIO-IA-001/
visual-authority/workshop-facelift-2026-08-02/
R17-voice-input-state-board-facelift.png (the six states) and doc 22 §W2d.

Covers services/workshop_voice_service.py, the transcription endpoint in
workshop_work_routes.py, the separate voice ceilings in
services/workshop_spend_guard.py, and the mic markup contract in the
Workshop templates.

No live network call is made anywhere in this file — Azure Speech is always
a stub. Every behavioural test uses a generic fixture key, never a
Pete-specific identifier.
"""

import io
import os
import shutil
import subprocess
import tempfile
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import app, limiter
from services import workshop_spend_guard
from services import workshop_voice_service
from services.speech_transcription_service import SpeechTranscriptionError


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

TRANSCRIBE_URL = "/app/workshop/voice/transcribe"

# A minimal but real WebM/Matroska header — validate_audio checks the
# container signature, so a body of arbitrary bytes would be rejected for the
# wrong reason and would never reach the code these tests are about.
WEBM_BYTES = b"\x1aE\xdf\xa3" + b"\x00" * 512


def webm_upload(data=None, filename="recording.webm"):
    return (io.BytesIO(WEBM_BYTES if data is None else data), filename, "audio/webm")


class StubSpeech:
    """Stands in for services/speech_transcription_service.

    It records exactly what it was handed so a test can assert the bytes
    reached the provider, and it can raise any normalized provider code.
    """

    def __init__(self, transcript="The prototype reduced integration time by three weeks.", error=None):
        self.transcript = transcript
        self.error = error
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append(
            SimpleNamespace(
                audio_bytes=audio_bytes, content_type=content_type, locale=locale
            )
        )
        if self.error is not None:
            raise SpeechTranscriptionError(self.error)
        return {
            "provider_transcript": self.transcript,
            "provider_request_id": "req-1",
            "duration_seconds": 3.0,
        }


# ---------------------------------------------------------------------------
# services/workshop_voice_service.py — the transcript-only contract
# ---------------------------------------------------------------------------


class WorkshopVoiceServiceTests(unittest.TestCase):
    def upload(self, data=None, mimetype="audio/webm"):
        return SimpleNamespace(
            stream=io.BytesIO(WEBM_BYTES if data is None else data),
            mimetype=mimetype,
        )

    def test_a_valid_recording_returns_the_transcript_text(self):
        speech = StubSpeech("I led the architecture review.")
        transcript = workshop_voice_service.transcribe_recording(
            self.upload(), "4.0", speech=speech
        )

        self.assertEqual(transcript, "I led the architecture review.")
        self.assertEqual(len(speech.calls), 1)
        self.assertEqual(speech.calls[0].audio_bytes, WEBM_BYTES)
        self.assertEqual(speech.calls[0].content_type, "audio/webm")

    def test_workshop_bounds_are_tighter_than_owner_voice_capture(self):
        """W2d's caps are its own, not the 3-minute/20 MB Capture draft's."""
        from services import voice_capture_service

        self.assertLess(
            workshop_voice_service.MAX_WORKSHOP_VOICE_SECONDS,
            voice_capture_service.MAX_VOICE_DURATION_SECONDS,
        )
        self.assertLess(
            workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES,
            voice_capture_service.MAX_VOICE_BYTES,
        )

    def test_a_recording_longer_than_the_cap_is_refused_before_the_provider(self):
        speech = StubSpeech()
        over = workshop_voice_service.MAX_WORKSHOP_VOICE_SECONDS + 1
        with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
            workshop_voice_service.transcribe_recording(
                self.upload(), str(over), speech=speech
            )

        self.assertEqual(caught.exception.code, "too-long")
        self.assertEqual(speech.calls, [], "an over-long recording must not be billed")

    def test_an_oversize_recording_is_refused_before_the_provider(self):
        speech = StubSpeech()
        too_big = WEBM_BYTES + b"\x00" * workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES
        with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
            workshop_voice_service.transcribe_recording(
                self.upload(too_big), "5.0", speech=speech
            )

        self.assertEqual(caught.exception.code, "too-large")
        self.assertEqual(speech.calls, [])

    def test_an_unsupported_container_is_refused(self):
        with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
            workshop_voice_service.transcribe_recording(
                self.upload(mimetype="application/zip"), "5.0", speech=StubSpeech()
            )
        self.assertEqual(caught.exception.code, "unsupported")

    def test_bytes_that_do_not_match_the_declared_type_are_refused(self):
        """The declared MIME type is not trusted on its own."""
        with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
            workshop_voice_service.transcribe_recording(
                self.upload(b"PK\x03\x04not-audio"), "5.0", speech=StubSpeech()
            )
        self.assertEqual(caught.exception.code, "unsupported")

    def test_provider_silence_becomes_an_honest_empty_speech_outcome(self):
        with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
            workshop_voice_service.transcribe_recording(
                self.upload(), "5.0", speech=StubSpeech(error="speech_empty")
            )
        self.assertEqual(caught.exception.code, "speech-empty")

    def test_a_blank_provider_transcript_is_never_returned_as_success(self):
        with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
            workshop_voice_service.transcribe_recording(
                self.upload(), "5.0", speech=StubSpeech(transcript="   ")
            )
        self.assertEqual(caught.exception.code, "speech-empty")

    def test_provider_outage_codes_map_to_unavailable(self):
        for code in ("speech_unavailable", "speech_auth_failed", "speech_timeout", "speech_busy"):
            with self.subTest(code=code):
                with self.assertRaises(workshop_voice_service.WorkshopVoiceError) as caught:
                    workshop_voice_service.transcribe_recording(
                        self.upload(), "5.0", speech=StubSpeech(error=code)
                    )
                self.assertEqual(caught.exception.code, "speech-unavailable")

    def test_every_outcome_code_has_honest_member_facing_copy(self):
        for code, message in workshop_voice_service.VOICE_ERROR_MESSAGES.items():
            with self.subTest(code=code):
                self.assertTrue(message.strip())
                self.assertNotIn("Error", message)
                self.assertNotIn("500", message)
        # Every message must leave the keyboard path standing.
        keyboard_paths = [
            message
            for message in workshop_voice_service.VOICE_ERROR_MESSAGES.values()
            if "typing" in message
        ]
        self.assertEqual(
            len(keyboard_paths), len(workshop_voice_service.VOICE_ERROR_MESSAGES)
        )

    def test_an_unknown_code_still_gets_an_honest_sentence(self):
        self.assertEqual(
            workshop_voice_service.message_for("something-new"),
            workshop_voice_service.DEFAULT_VOICE_ERROR_MESSAGE,
        )

    def test_a_transcript_is_capped_before_it_reaches_the_browser(self):
        long_text = "word " * 5000
        transcript = workshop_voice_service.transcribe_recording(
            self.upload(), "5.0", speech=StubSpeech(long_text)
        )
        self.assertLessEqual(
            len(transcript), workshop_voice_service.MAX_TRANSCRIPT_CHARS
        )


class AudioIsNotRetainedTests(unittest.TestCase):
    """The load-bearing privacy property: PeerSlate keeps the transcript and
    not the recording. Proven three ways rather than asserted in prose."""

    def upload(self):
        return SimpleNamespace(stream=io.BytesIO(WEBM_BYTES), mimetype="audio/webm")

    def test_the_module_imports_no_storage_or_database_collaborator(self):
        """The strongest available proof: it cannot persist audio because it
        holds no client that could."""
        names = dir(workshop_voice_service)
        for forbidden in (
            "media_storage_service",
            "database_service",
            "knowledge_service",
            "session",
        ):
            self.assertNotIn(forbidden, names)

    def test_transcribing_writes_no_file_anywhere_under_the_instance_path(self):
        directory = tempfile.mkdtemp(prefix="ps-workshop-voice-retention-")
        original = app.instance_path
        app.instance_path = directory
        try:
            before = self._tree(directory)
            workshop_voice_service.transcribe_recording(
                self.upload(), "4.0", speech=StubSpeech()
            )
            self.assertEqual(self._tree(directory), before)
        finally:
            app.instance_path = original
            shutil.rmtree(directory, ignore_errors=True)

    def test_a_full_request_never_calls_blob_storage_or_sql(self):
        """The route, not just the service: nothing on the real request path
        reaches the collaborators that could keep a recording."""
        client = app.test_client()
        with voice_flags_on(), spend_state():
            with patch(
                "services.media_storage_service.media_storage_service.upload"
            ) as upload, patch(
                "services.database_service.database_service.execute_procedure"
            ) as query, patch(
                "workshop_work_routes.workshop_voice_service.speech_transcription_service",
                StubSpeech(),
            ):
                response = client.post(
                    TRANSCRIBE_URL,
                    data={"audio": webm_upload(), "duration_seconds": "4.0"},
                    content_type="multipart/form-data",
                    headers=SAME_ORIGIN_HEADERS,
                )

        self.assertEqual(response.status_code, 200)
        upload.assert_not_called()
        query.assert_not_called()

    @staticmethod
    def _tree(directory):
        found = []
        for base, _dirs, files in os.walk(directory):
            for name in files:
                found.append(os.path.join(base, name))
        return sorted(found)


# ---------------------------------------------------------------------------
# Shared route fixtures
# ---------------------------------------------------------------------------


class _FlagContext:
    def __init__(self, **flags):
        self.flags = flags
        self.original = {}

    def __enter__(self):
        for key, value in self.flags.items():
            self.original[key] = app.config.get(key)
            app.config[key] = value
        return self

    def __exit__(self, *exc):
        for key, value in self.original.items():
            app.config[key] = value
        return False


def voice_flags_on(voice=True):
    return _FlagContext(
        PEERSLATE_WORKSHOP_ENABLED=True,
        PEERSLATE_WORKSHOP_SESSION_ENABLED=True,
        PEERSLATE_WORKSHOP_VOICE_ENABLED=voice,
    )


class _SpendState:
    """A private instance path so no test consumes another's daily budget."""

    def __enter__(self):
        self.directory = tempfile.mkdtemp(prefix="ps-workshop-voice-spend-")
        self.original = app.instance_path
        app.instance_path = self.directory
        return self

    def __exit__(self, *exc):
        app.instance_path = self.original
        shutil.rmtree(self.directory, ignore_errors=True)
        return False


def spend_state():
    return _SpendState()


class VoiceRouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self._flags = voice_flags_on()
        self._flags.__enter__()
        self._spend = spend_state()
        self._spend.__enter__()
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        self._spend.__exit__(None, None, None)
        self._flags.__exit__(None, None, None)

    def post(self, speech=None, headers=None, duration="4.0", data=None, url=None):
        payload = {"audio": webm_upload(), "duration_seconds": duration}
        if data is not None:
            payload = data
        with patch(
            "workshop_work_routes.workshop_voice_service.speech_transcription_service",
            speech or StubSpeech(),
        ):
            return self.client.post(
                url or TRANSCRIBE_URL,
                data=payload,
                content_type="multipart/form-data",
                headers=SAME_ORIGIN_HEADERS if headers is None else headers,
            )


# ---------------------------------------------------------------------------
# The endpoint
# ---------------------------------------------------------------------------


class TranscriptionEndpointTests(VoiceRouteTestCase):
    def test_a_valid_recording_returns_only_a_transcript(self):
        response = self.post(StubSpeech("I rebuilt the intake flow."))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"transcript": "I rebuilt the intake flow."})

    def test_the_response_is_private_and_never_cached(self):
        response = self.post()
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_no_provider_payload_or_request_id_reaches_the_browser(self):
        response = self.post()
        self.assertEqual(list(response.get_json()), ["transcript"])

    def test_the_endpoint_never_resolves_identity(self):
        """It reads and writes nothing owner-scoped, so it must not even ask
        who the caller is — that is what makes anonymous and member callers
        provably the same code path."""
        with patch("workshop_work_routes.get_current_identity") as identity:
            response = self.post()

        self.assertEqual(response.status_code, 200)
        identity.assert_not_called()

    def test_an_anonymous_caller_never_reaches_an_owner_scoped_service(self):
        with patch(
            "services.knowledge_service.knowledge_service.save_knowledge_item_for_owner"
        ) as save, patch(
            "services.knowledge_service.knowledge_service.list_knowledge_items_for_owner"
        ) as lister:
            response = self.post()

        self.assertEqual(response.status_code, 200)
        save.assert_not_called()
        lister.assert_not_called()


class FlagGateTests(VoiceRouteTestCase):
    def test_the_endpoint_404s_when_the_voice_flag_is_off(self):
        with voice_flags_on(voice=False):
            response = self.post()
        self.assertEqual(response.status_code, 404)

    def test_the_endpoint_404s_when_the_outer_workshop_flag_is_off(self):
        with _FlagContext(PEERSLATE_WORKSHOP_ENABLED=False):
            response = self.post()
        self.assertEqual(response.status_code, 404)

    def test_the_endpoint_404s_when_the_session_sub_flag_is_off(self):
        with _FlagContext(PEERSLATE_WORKSHOP_SESSION_ENABLED=False):
            response = self.post()
        self.assertEqual(response.status_code, 404)

    def test_the_flag_gate_runs_before_the_provider_is_ever_touched(self):
        speech = StubSpeech()
        with voice_flags_on(voice=False):
            self.post(speech)
        self.assertEqual(speech.calls, [])

    def test_the_flag_defaults_to_off(self):
        """It ships merged and dark; enablement is a separate decision."""
        source = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
        self.assertIn(
            "os.environ.get('PEERSLATE_WORKSHOP_VOICE_ENABLED', 'false')", source
        )


class SameOriginTests(VoiceRouteTestCase):
    def test_a_cross_site_post_is_refused(self):
        response = self.post(
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"}
        )
        self.assertEqual(response.status_code, 403)

    def test_a_post_with_no_origin_evidence_at_all_fails_closed(self):
        response = self.post(headers={})
        self.assertEqual(response.status_code, 403)

    def test_a_refused_cross_site_post_never_reaches_the_provider(self):
        speech = StubSpeech()
        self.post(
            speech,
            headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"},
        )
        self.assertEqual(speech.calls, [], "a refused request must cost nothing")


class HonestFailureTests(VoiceRouteTestCase):
    def test_a_provider_failure_returns_honest_copy_and_no_transcript(self):
        """A recording Azure could not process is the provider's condition,
        not a malformed request, so it must not be logged as a client 400."""
        response = self.post(StubSpeech(error="speech_failed"))

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["error"], "transcription-failed")
        self.assertIn("couldn't transcribe", payload["message"])
        self.assertNotIn("transcript", payload)

    def test_a_provider_outage_is_a_503_with_honest_copy(self):
        response = self.post(StubSpeech(error="speech_unavailable"))

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["error"], "speech-unavailable")
        self.assertIn("keep typing", payload["message"])

    def test_silence_is_reported_as_silence_not_as_a_broken_service(self):
        response = self.post(StubSpeech(error="speech_empty"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "speech-empty")

    def test_an_oversize_recording_is_refused_honestly(self):
        oversize = WEBM_BYTES + b"\x00" * workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES
        speech = StubSpeech()
        response = self.post(
            speech,
            data={
                "audio": webm_upload(oversize),
                "duration_seconds": "4.0",
            },
        )

        # Either the endpoint's own byte cap or Werkzeug's raised
        # content-length ceiling refuses it — both are honest refusals, and
        # neither reaches the provider.
        self.assertIn(response.status_code, (400, 413))
        self.assertEqual(speech.calls, [])

    def test_an_over_long_recording_is_refused_honestly(self):
        speech = StubSpeech()
        response = self.post(
            speech,
            duration=str(workshop_voice_service.MAX_WORKSHOP_VOICE_SECONDS + 5),
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["error"], "too-long")
        self.assertIn(
            str(workshop_voice_service.MAX_WORKSHOP_VOICE_SECONDS), payload["message"]
        )
        self.assertEqual(speech.calls, [])

    def test_a_missing_recording_is_refused_honestly(self):
        response = self.post(data={"duration_seconds": "4.0"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "required")

    def test_every_failure_response_still_tells_the_member_they_can_type(self):
        for error in ("speech_failed", "speech_unavailable", "speech_empty"):
            with self.subTest(error=error):
                payload = self.post(StubSpeech(error=error)).get_json()
                self.assertIn("typing", payload["message"])


class BoundedUploadTests(VoiceRouteTestCase):
    def test_the_endpoint_raises_the_global_body_limit_only_for_itself(self):
        """The app-wide 2 MB form limit would refuse a legitimate recording,
        so the cap is raised for this one endpoint and nothing else."""
        self.assertGreater(
            workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES,
            app.config["MAX_CONTENT_LENGTH"],
        )

        seen = {}

        original = workshop_voice_service.transcribe_recording

        def record(*args, **kwargs):
            from flask import request as flask_request

            seen["limit"] = flask_request.max_content_length
            return original(*args, **kwargs)

        with patch(
            "workshop_work_routes.workshop_voice_service.transcribe_recording", record
        ):
            self.post()

        self.assertEqual(
            seen["limit"],
            workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES + (64 * 1024),
        )

    def test_another_workshop_route_keeps_the_small_global_limit(self):
        seen = {}

        with app.test_request_context("/app/workshop/work"):
            from flask import request as flask_request

            seen["limit"] = flask_request.max_content_length

        self.assertNotEqual(
            seen["limit"],
            workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES + (64 * 1024),
        )


class VoiceSpendCeilingTests(VoiceRouteTestCase):
    def test_a_transcription_reserves_before_the_provider_call(self):
        with patch(
            "workshop_work_routes.workshop_spend_guard.reserve_voice",
            return_value=workshop_spend_guard.RESERVE_OK,
        ) as reserve:
            response = self.post()

        self.assertEqual(response.status_code, 200)
        reserve.assert_called_once()

    def test_a_capped_caller_is_refused_before_the_provider_is_billed(self):
        speech = StubSpeech()
        with patch(
            "workshop_work_routes.workshop_spend_guard.reserve_voice",
            return_value=workshop_spend_guard.RESERVE_IP_CAPPED,
        ):
            response = self.post(speech)

        self.assertEqual(response.status_code, 429)
        payload = response.get_json()
        self.assertEqual(payload["error"], "voice-daily-limit")
        self.assertIn("keep typing", payload["message"])
        self.assertEqual(speech.calls, [])

    def test_voice_and_ai_review_have_separate_daily_budgets(self):
        """Different vendors, different bills — exhausting one must never
        exhaust the other."""
        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "203.0.113.5"}):
            for _ in range(workshop_spend_guard.PER_IP_DAILY_VOICE_TRANSCRIPTIONS):
                self.assertEqual(
                    workshop_spend_guard.reserve_voice("203.0.113.5"),
                    workshop_spend_guard.RESERVE_OK,
                )
            self.assertEqual(
                workshop_spend_guard.reserve_voice("203.0.113.5"),
                workshop_spend_guard.RESERVE_IP_CAPPED,
            )
            # The Anthropic budget for the same address is untouched.
            self.assertEqual(
                workshop_spend_guard.reserve("203.0.113.5"),
                workshop_spend_guard.RESERVE_OK,
            )

    def test_exhausting_ai_review_does_not_disable_voice(self):
        with app.test_request_context("/", environ_base={"REMOTE_ADDR": "203.0.113.6"}):
            for _ in range(workshop_spend_guard.PER_IP_DAILY_AI_CALLS):
                workshop_spend_guard.reserve("203.0.113.6")
            self.assertEqual(
                workshop_spend_guard.reserve("203.0.113.6"),
                workshop_spend_guard.RESERVE_IP_CAPPED,
            )
            self.assertEqual(
                workshop_spend_guard.reserve_voice("203.0.113.6"),
                workshop_spend_guard.RESERVE_OK,
            )

    def test_the_global_voice_ceiling_bounds_every_address_together(self):
        with app.test_request_context("/"):
            for index in range(workshop_spend_guard.GLOBAL_DAILY_VOICE_TRANSCRIPTIONS):
                address = "198.51.100.%d" % (index % 200)
                outcome = workshop_spend_guard.reserve_voice(address)
                if outcome != workshop_spend_guard.RESERVE_OK:
                    break
            self.assertEqual(
                workshop_spend_guard.reserve_voice("198.51.100.250"),
                workshop_spend_guard.RESERVE_GLOBAL_CAPPED,
            )

    def test_both_budgets_survive_each_other_in_the_same_state_file(self):
        """A shared file must not let one kind's write zero the other's."""
        with app.test_request_context("/"):
            workshop_spend_guard.reserve("192.0.2.10")
            workshop_spend_guard.reserve_voice("192.0.2.10")
            workshop_spend_guard.reserve("192.0.2.10")

            import json

            with open(workshop_spend_guard.state_path(), encoding="utf-8") as handle:
                state = json.load(handle)

        self.assertEqual(state["global_count"], 2)
        self.assertEqual(state["voice_global_count"], 1)
        self.assertEqual(state["per_ip"]["192.0.2.10"], 2)
        self.assertEqual(state["voice_per_ip"]["192.0.2.10"], 1)


class RateLimitRegistrationTests(unittest.TestCase):
    def test_the_transcription_endpoint_is_rate_limited(self):
        source = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
        self.assertIn("('workshop.transcribe_voice', '8 per minute')", source)




# ---------------------------------------------------------------------------
# Template contract — R17's mic goes on authored text and nowhere else
# ---------------------------------------------------------------------------


VOICE_FIELD_TEMPLATES = {
    "templates/workshop_work.html": "wk-work-thought",
    "templates/workshop_work_session.html": "wk-session-answer",
    "templates/workshop_work_review.html": "wk-followup-answer",
    "templates/workshop_add.html": "wk-wording",
    "templates/workshop_review.html": "wk-review-wording",
}


def read_template(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


class MicMarkupContractTests(unittest.TestCase):
    def test_every_authored_text_field_uses_the_shared_voice_macro(self):
        for template, field_id in VOICE_FIELD_TEMPLATES.items():
            with self.subTest(template=template):
                body = read_template(template)
                self.assertIn("workshop_mic", body)
                self.assertIn(field_id, body)

    def test_no_template_still_hard_codes_the_old_inert_mic(self):
        """The inert markup lives in exactly one macro now, so the honest
        'not available yet' sentence cannot drift between screens."""
        for template in VOICE_FIELD_TEMPLATES:
            with self.subTest(template=template):
                body = read_template(template)
                self.assertNotIn('aria-label="Voice input is not available yet"', body)

    def test_the_library_search_field_never_gets_a_voice_mic(self):
        """Doc 20 §6a: filters, navigation, and search are not authored
        text. Search keeps its own inert control and is never wired."""
        body = read_template("templates/partials/workshop/_library.html")
        self.assertIn("wk-search__mic", body)
        self.assertNotIn("workshop_mic", body)
        self.assertNotIn("data-wk-voice", body)

    def test_the_macro_renders_the_real_control_only_behind_the_flag(self):
        macro = read_template("templates/partials/workshop/_voice.html")
        self.assertIn("workshop_voice_enabled", macro)
        self.assertIn("data-wk-voice", macro)
        self.assertIn("not available yet", macro)


class RenderedMicTests(unittest.TestCase):
    """What actually reaches the browser, flag on and flag off."""

    def setUp(self):
        self.client = app.test_client()
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled

    def opening(self):
        return self.client.get("/app/workshop/work").data.decode("utf-8")

    def test_flag_off_renders_the_same_honest_inert_mic_as_today(self):
        with voice_flags_on(voice=False):
            body = self.opening()

        self.assertIn("wk-mic-btn", body)
        self.assertIn("not available yet", body)
        self.assertNotIn("data-wk-voice", body)

    def test_flag_on_renders_the_real_mic_but_inert_until_the_script_runs(self):
        """Supersedes ``test_flag_on_renders_a_real_keyboard_operable_mic_
        button``, whose "a real control, never a disabled one" expectation
        was itself the accessibility defect (audit P7a, 2026-08-04).

        The flag-on page still ships the REAL six-state control — the wiring,
        the endpoint, the state machine. What it no longer ships is the
        PROMISE: with JavaScript off or a script that fails to load, that
        button used to sit there focusable and labelled "Speak your thought"
        while doing nothing. The server now renders it disabled and honestly
        labelled, and workshop-voice.js enables it on first render, so the
        affordance appears exactly when something can honour it."""
        with voice_flags_on():
            body = self.opening()

        # The real control, with its real wiring, is present.
        self.assertIn("data-wk-voice", body)
        self.assertIn("data-wk-voice-mic", body)
        self.assertIn("wk-mic-btn--live", body)
        self.assertIn('type="button"', body)

        # ...but inert and honest until the script upgrades it.
        self.assertIn('aria-label="Voice input is not available yet"', body)
        self.assertIn('aria-disabled="true"', body)
        self.assertNotIn('aria-label="Speak your thought"', body)

    def test_the_script_is_what_enables_the_mic(self):
        """The other half of the contract above: if this ever stops being
        true, the flag-on mic is permanently dead rather than merely
        honest."""
        script = read_template("static/js/workshop-voice.js")
        self.assertIn("micButton.disabled = state === TRANSCRIBING;", script)
        self.assertIn("micButton.removeAttribute('aria-disabled');", script)
        self.assertIn("'Speak your ' + noun", script)

    def test_no_cancel_control_is_visible_before_a_recording_starts(self):
        """R17 state 1 has no Cancel. It must be hidden in the markup itself,
        not only once JavaScript first paints — a real defect found in the
        Playwright pass, where Cancel sat on top of the mic in the ready
        state because onChange only fires on a transition."""
        with voice_flags_on():
            body = self.opening()

        import re

        tags = re.findall(r"<button[^>]*data-wk-voice-cancel[^>]*>", body)
        self.assertTrue(tags, "the Cancel control should render")
        for tag in tags:
            self.assertIn("hidden", tag)

    def test_flag_on_announces_state_changes_politely(self):
        with voice_flags_on():
            body = self.opening()
        self.assertIn('aria-live="polite"', body)

    def test_the_transcription_url_is_emitted_rather_than_hard_coded(self):
        with voice_flags_on():
            body = self.opening()
        self.assertIn(TRANSCRIBE_URL, body)

    def test_the_composer_still_works_with_no_javascript_at_all(self):
        """Voice is strictly additive: the server-rendered form is complete
        on its own, so a browser that runs no JS loses only the mic."""
        with voice_flags_on():
            body = self.opening()

        self.assertIn('name="thought"', body)
        self.assertIn('type="submit"', body)
        self.assertIn("/app/workshop/work/start", body)

    def test_the_voice_script_is_only_loaded_when_the_flag_is_on(self):
        with voice_flags_on(voice=False):
            self.assertNotIn("workshop-voice.js", self.opening())
        with voice_flags_on():
            self.assertIn("workshop-voice.js", self.opening())


# ---------------------------------------------------------------------------
# The browser state machine — six states, run in Node against the real module
# ---------------------------------------------------------------------------


class VoiceStateMachineTests(unittest.TestCase):
    """static/js/workshop-voice.js's state machine is production code with no
    DOM dependency, so it is executed directly rather than asserted about.

    Driven from Python by subprocess in the same way
    tests/test_community_tabs.py drives tests/community_focus_lifecycle.test.js
    — this repository has no npm/jest harness, and adding one for a single
    module would be a larger change than the module itself.
    """

    def test_the_six_states_and_their_transitions_hold(self):
        node = shutil.which("node")
        app_node = "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node"
        if not node and os.path.isfile(app_node):
            node = app_node
        if not node:
            self.skipTest("Node is not available to run the JS state-machine tests.")

        result = subprocess.run(
            [node, os.path.join(ROOT, "tests", "workshop_voice.test.js")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()


class DictationInsertionPointTests(unittest.TestCase):
    """Audit follow-on (2026-08-04): a transcript landed at position 0 when
    the field had never been focused.

    A textarea that has never held a caret reports ``selectionStart === 0``
    — a real number, not undefined — so the caret-aware insertion treated
    "never touched" as "caret at the very beginning". Someone who typed a
    paragraph and then pressed the mic watched their dictation land in front
    of everything they had written.

    Asserted against the shared module's source, matching this repo's
    existing convention for behaviour that lives in a browser script
    (see tests/test_interview_studio.py's own dictation assertions).
    """

    def _module(self):
        return (
            pathlib.Path(__file__).resolve().parents[1] / "static" / "js" / "dictation.js"
        ).read_text(encoding="utf-8")

    def test_the_caret_is_only_trusted_for_a_field_that_has_held_one(self):
        module = self._module()
        self.assertIn("CARET_KNOWN_FIELDS", module)
        self.assertIn("hasRealCaret", module)
        self.assertIn("var caretIsReal = hasRealCaret(target);", module)
        # Both ends of the selection must respect it, or a stale selectionEnd
        # would still splice into the middle.
        self.assertIn("caretIsReal && typeof target.selectionStart === 'number'", module)
        self.assertIn("caretIsReal && typeof target.selectionEnd === 'number'", module)

    def test_an_untouched_field_appends_at_the_end(self):
        module = self._module()
        self.assertIn("? target.selectionStart\n            : target.value.length;", module)

    def test_focus_is_tracked_by_listener_not_by_active_element(self):
        """Pressing the mic moves focus to the BUTTON, so checking
        document.activeElement at insertion time would report "not focused"
        for every dictation and break deliberate mid-text insertion."""
        module = self._module()
        self.assertIn("'focusin'", module)
        self.assertNotIn("document.activeElement === target", module)

    def test_it_degrades_rather_than_guessing_without_weakset(self):
        module = self._module()
        self.assertIn("if (!CARET_KNOWN_FIELDS) return true;", module)
