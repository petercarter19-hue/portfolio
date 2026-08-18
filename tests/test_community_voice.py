"""Protected contracts for the request-only Community Voice comment slice."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "community-voice-test-key")

from app import app, limiter
from services.community_voice_service import (
    CommunityVoiceError,
    CommunityVoiceService,
    community_voice_service,
)
from services.speech_transcription_service import SpeechTranscriptionError
from services.voice_capture_service import MAX_VOICE_BYTES


WEBM = b"\x1aE\xdf\xa3" + b"local-voice-fixture"
OWNER_KEY = str(uuid4())
OTHER_KEY = str(uuid4())
ROOT = Path(__file__).resolve().parents[1]


class Upload:
    mimetype = "audio/webm"

    def __init__(self, payload=WEBM):
        self.stream = io.BytesIO(payload)


class CommunityVoiceServiceTests(unittest.TestCase):
    def setUp(self):
        self.speech = Mock()
        self.service = CommunityVoiceService(speech=self.speech)

    def test_returns_only_bounded_review_proposal_without_persistence_dependencies(self):
        self.speech.transcribe.return_value = {
            "provider_transcript": "  A reviewed transcript proposal.  ",
            "provider_request_id": "provider-private-id",
            "duration_seconds": 4.2,
        }

        proposal = self.service.transcribe(Upload(), "1.25", "contribution")

        self.assertEqual(
            proposal,
            {
                "text": "A reviewed transcript proposal.",
                "composer_context": "contribution",
                "max_utf16_code_units": 2000,
            },
        )
        self.speech.transcribe.assert_called_once_with(WEBM, "audio/webm", "en-US")
        self.assertNotIn("provider", str(proposal).lower())
        self.assertFalse(hasattr(self.service, "database"))
        self.assertFalse(hasattr(self.service, "storage"))

    def test_rejects_invalid_audio_context_empty_and_utf16_overflow_without_truncation(self):
        self.speech.transcribe.return_value = {
            "provider_transcript": "🙂" * 1001,
            "duration_seconds": 1,
        }
        with self.assertRaisesRegex(CommunityVoiceError, "transcript-too-long"):
            self.service.transcribe(Upload(), "1", "contribution")
        with self.assertRaisesRegex(CommunityVoiceError, "invalid-context"):
            self.service.transcribe(Upload(), "1", "reply")
        self.speech.transcribe.return_value = {
            "provider_transcript": "   ",
            "duration_seconds": 1,
        }
        with self.assertRaisesRegex(CommunityVoiceError, "provider-response-invalid"):
            self.service.transcribe(Upload(), "1", "post")
        with self.assertRaisesRegex(CommunityVoiceError, "recording-too-long"):
            self.service.transcribe(Upload(), "181", "post")

    def test_normalizes_provider_failure_without_provider_detail(self):
        self.speech.transcribe.side_effect = RuntimeError("PRIVATE PROVIDER BODY")
        with self.assertRaisesRegex(CommunityVoiceError, "transcription-unavailable") as raised:
            self.service.transcribe(Upload(), "1", "contribution")
        self.assertNotIn("PRIVATE", str(raised.exception))

    def test_preserves_only_safe_adapter_classifications(self):
        expected = {
            "speech_empty": "speech-empty",
            "speech_timeout": "speech-timeout",
            "speech_busy": "speech-busy",
            "speech_unavailable": "transcription-unavailable",
            "speech_auth_failed": "transcription-unavailable",
            "speech_failed": "transcription-failed",
            "speech_malformed": "provider-response-invalid",
            "unsupported_locale": "unsupported-locale",
            "private_provider_code": "transcription-unavailable",
        }
        for adapter_code, community_code in expected.items():
            with self.subTest(adapter_code=adapter_code):
                self.speech.transcribe.side_effect = SpeechTranscriptionError(
                    adapter_code
                )
                with self.assertRaisesRegex(
                    CommunityVoiceError, community_code
                ) as raised:
                    self.service.transcribe(Upload(), "1", "contribution")
                self.assertNotIn(adapter_code, str(raised.exception))

    def test_malformed_provider_result_is_retryable_instead_of_an_empty_transcript_claim(self):
        for result in (
            None,
            {},
            {"provider_transcript": None},
            {"provider_transcript": "text", "duration_seconds": None},
            {"provider_transcript": "text", "duration_seconds": "invalid"},
            {"provider_transcript": "text", "duration_seconds": float("nan")},
        ):
            with self.subTest(result=result):
                self.speech.transcribe.return_value = result
                with self.assertRaisesRegex(
                    CommunityVoiceError, "provider-response-invalid"
                ):
                    self.service.transcribe(Upload(), "1", "contribution")

    def test_rejects_provider_measured_duration_over_three_minutes(self):
        self.speech.transcribe.return_value = {
            "provider_transcript": "This client claimed one second.",
            "duration_seconds": 180.01,
        }
        with self.assertRaisesRegex(CommunityVoiceError, "recording-too-long"):
            self.service.transcribe(Upload(), "1", "contribution")


class CommunityVoiceRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous_config = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY=OWNER_KEY,
            PEERSLATE_OWNER_USER_KEYS=OWNER_KEY,
            PEERSLATE_OWNER_EMAILS="",
            PEERSLATE_COMMUNITY_SIGNING_KEY="community-voice-test-signing-key",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous_config)

    @staticmethod
    def headers(**extra):
        return {"X-PeerSlate-Request": "same-origin", **extra}

    @staticmethod
    def form(**extra):
        return {
            "audio": (io.BytesIO(WEBM), "voice.webm", "audio/webm"),
            "duration_seconds": "1.2",
            "composer_context": "contribution",
            **extra,
        }

    @patch("community_api.community_voice_service.transcribe")
    def test_owner_multipart_route_returns_no_store_review_proposal_only(self, transcribe):
        transcribe.return_value = {
            "text": "A reviewable transcript.",
            "composer_context": "contribution",
            "max_utf16_code_units": 2000,
        }
        response = self.client.post(
            "/api/v1/community/voice/transcriptions",
            data=self.form(),
            headers=self.headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.get_json()["proposal"]["text"], "A reviewable transcript.")
        transcribe.assert_called_once()
        self.assertNotIn("owner", str(transcribe.call_args.kwargs).lower())

    @patch("community_api.community_voice_service.transcribe")
    def test_route_denies_signed_out_non_owner_cross_origin_and_flag_off(self, transcribe):
        app.config["PEERSLATE_DEV_USER_KEY"] = None
        signed_out = self.client.post(
            "/api/v1/community/voice/transcriptions", data=self.form(),
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual((signed_out.status_code, signed_out.get_json()["code"]), (401, "authentication_required"))
        app.config["PEERSLATE_DEV_USER_KEY"] = OTHER_KEY
        non_owner = self.client.post(
            "/api/v1/community/voice/transcriptions", data=self.form(),
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual((non_owner.status_code, non_owner.get_json()["code"]), (403, "action_unavailable"))
        app.config["PEERSLATE_DEV_USER_KEY"] = OWNER_KEY
        cross_origin = self.client.post(
            "/api/v1/community/voice/transcriptions", data=self.form(),
            headers=self.headers(Origin="https://attacker.example"), content_type="multipart/form-data"
        )
        self.assertEqual((cross_origin.status_code, cross_origin.get_json()["code"]), (403, "same_origin_required"))
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False
        off = self.client.post(
            "/api/v1/community/voice/transcriptions", data=self.form(),
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual((off.status_code, off.get_json()["code"]), (404, "not_found"))
        transcribe.assert_not_called()

    @patch("community_api.community_voice_service.transcribe")
    def test_route_rejects_wrong_content_unknown_fields_and_missing_recording(self, transcribe):
        multipart = self.client.post(
            "/api/v1/community/voice/transcriptions", json={}, headers=self.headers()
        )
        self.assertEqual((multipart.status_code, multipart.get_json()["code"]), (415, "multipart_required"))
        unknown = self.client.post(
            "/api/v1/community/voice/transcriptions", data=self.form(extra="nope"),
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual((unknown.status_code, unknown.get_json()["code"]), (422, "invalid_context"))
        missing = self.client.post(
            "/api/v1/community/voice/transcriptions",
            data={"duration_seconds": "1", "composer_context": "contribution"},
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual((missing.status_code, missing.get_json()["code"]), (422, "recording_required"))
        missing_duration = self.client.post(
            "/api/v1/community/voice/transcriptions",
            data={
                "audio": (io.BytesIO(WEBM), "voice.webm", "audio/webm"),
                "composer_context": "contribution",
            },
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual(
            (missing_duration.status_code, missing_duration.get_json()["code"]),
            (422, "invalid_duration"),
        )
        missing_context = self.client.post(
            "/api/v1/community/voice/transcriptions",
            data={
                "audio": (io.BytesIO(WEBM), "voice.webm", "audio/webm"),
                "duration_seconds": "1",
            },
            headers=self.headers(), content_type="multipart/form-data"
        )
        self.assertEqual(
            (missing_context.status_code, missing_context.get_json()["code"]),
            (422, "invalid_context"),
        )
        transcribe.assert_not_called()

    @patch("community_api.community_voice_service.transcribe")
    def test_route_normalizes_service_failure_and_never_logs_content(self, transcribe):
        transcribe.side_effect = CommunityVoiceError("transcription-unavailable")
        with patch.object(app.logger, "warning") as log:
            response = self.client.post(
                "/api/v1/community/voice/transcriptions", data=self.form(),
                headers=self.headers(), content_type="multipart/form-data"
            )
        payload = response.get_json()
        self.assertEqual((response.status_code, payload["code"]), (503, "transcription_unavailable"))
        self.assertEqual((payload["retry"], payload["retryable"]), ("none", False))
        self.assertNotIn("provider", str(payload).lower())
        self.assertNotIn("voice.webm", repr(log.call_args))
        self.assertEqual(log.call_args.args, ("Community Voice transcription unavailable.",))

    @patch("community_api.community_voice_service.transcribe")
    def test_route_exposes_truthful_additive_retry_contract(self, transcribe):
        cases = {
            "speech-empty": (422, "no_speech", "new_recording"),
            "speech-timeout": (503, "provider_timeout", "same_recording"),
            "speech-busy": (503, "provider_busy", "same_recording"),
            "transcription-unavailable": (503, "transcription_unavailable", "none"),
            "transcription-failed": (503, "transcription_failed", "new_recording"),
            "unsupported-locale": (422, "recording_invalid", "none"),
            "provider-response-invalid": (503, "provider_response_invalid", "same_recording"),
            "recording-too-large": (413, "recording_too_large", "new_recording"),
            "transcript-too-long": (422, "transcript_too_long", "new_recording"),
        }
        for service_code, expected in cases.items():
            with self.subTest(service_code=service_code):
                transcribe.side_effect = CommunityVoiceError(service_code)
                response = self.client.post(
                    "/api/v1/community/voice/transcriptions",
                    data=self.form(),
                    headers=self.headers(),
                    content_type="multipart/form-data",
                )
                payload = response.get_json()
                status, code, retry = expected
                self.assertEqual((response.status_code, payload["code"]), (status, code))
                self.assertEqual(payload["retry"], retry)
                self.assertEqual(payload["retryable"], retry == "same_recording")
                self.assertNotIn("speech_", str(payload).lower())
                self.assertNotIn("request_id", str(payload).lower())

    def test_adapter_empty_result_reaches_route_as_no_speech_not_unavailable(self):
        with patch.object(
            community_voice_service.speech,
            "transcribe",
            side_effect=SpeechTranscriptionError("speech_empty"),
        ):
            response = self.client.post(
                "/api/v1/community/voice/transcriptions",
                data=self.form(),
                headers=self.headers(),
                content_type="multipart/form-data",
            )
        payload = response.get_json()
        self.assertEqual((response.status_code, payload["code"]), (422, "no_speech"))
        self.assertEqual((payload["retry"], payload["retryable"]), ("new_recording", False))
        self.assertNotIn("speech_empty", str(payload))

    def test_route_source_keeps_the_twenty_per_hour_limit_and_voice_ceiling(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        api_source = (ROOT / "community_api.py").read_text(encoding="utf-8")
        self.assertIn("'community_api.transcribe_voice': '20 per hour'", source)
        self.assertIn("VOICE_MULTIPART_LIMIT = MAX_VOICE_BYTES + 64 * 1024", api_source)
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], 2 * 1024 * 1024)

    @patch("community_api.community_voice_service.transcribe")
    def test_route_checks_oversized_content_before_transcription(self, transcribe):
        response = self.client.post(
            "/api/v1/community/voice/transcriptions",
            data={
                "audio": (
                    io.BytesIO(b"\x1aE\xdf\xa3" + b"x" * (MAX_VOICE_BYTES + 64 * 1024)),
                    "voice.webm",
                    "audio/webm",
                ),
                "duration_seconds": "1",
                "composer_context": "contribution",
            },
            headers=self.headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["code"], "recording_too_large")
        transcribe.assert_not_called()

    @patch("community_api.community_voice_service.transcribe")
    def test_route_maps_service_file_limit_to_413(self, transcribe):
        transcribe.side_effect = CommunityVoiceError("recording-too-large")
        response = self.client.post(
            "/api/v1/community/voice/transcriptions",
            data=self.form(),
            headers=self.headers(),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()["code"], "recording_too_large")

    @patch("community_api.community_voice_service.transcribe")
    def test_route_is_limited_to_twenty_transcription_requests_per_hour(self, transcribe):
        transcribe.return_value = {
            "text": "Local proposal.",
            "composer_context": "contribution",
            "max_utf16_code_units": 2000,
        }
        was_enabled = limiter.enabled
        limiter.enabled = True
        limiter.storage.reset()
        try:
            responses = [
                self.client.post(
                    "/api/v1/community/voice/transcriptions", data=self.form(),
                    headers=self.headers(), content_type="multipart/form-data"
                )
                for _ in range(21)
            ]
        finally:
            limiter.storage.reset()
            limiter.enabled = was_enabled
        self.assertEqual([response.status_code for response in responses[:20]], [200] * 20)
        self.assertEqual(responses[-1].status_code, 429)
        self.assertEqual(responses[-1].get_json()["code"], "voice_rate_limited")
        self.assertEqual(
            (responses[-1].get_json()["retry"], responses[-1].get_json()["retryable"]),
            ("none", False),
        )


class CommunityVoiceFrontendContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "static" / "js" / "community-v1.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static" / "css" / "community-v1.css").read_text(encoding="utf-8")
        cls.template = (ROOT / "templates" / "community_feed.html").read_text(encoding="utf-8")
        cls.policy = (ROOT / "templates" / "community_pilot_policy.html").read_text(encoding="utf-8")

    def test_reusable_a_to_h_controller_propagates_only_to_approved_composers(self):
        controller = self.script[
            self.script.index("function CommunityVoiceController"):
            self.script.index("function resizePrimaryComment")
        ]
        for state in ("permission", "recording", "processing", "preview", "ready-to-send"):
            self.assertIn(state, controller)
        self.assertIn("communityVoiceRegistry", controller)
        self.assertIn("window.setTimeout", controller)
        self.assertIn("180000", controller)
        self.assertIn("this.durationSeconds", controller)
        self.assertIn("voiceElapsedLabel", controller)
        self.assertIn("cv1-comment-voice-processing", controller)
        self.assertIn("data.append('duration_seconds', String(this.durationSeconds || .01))", controller)
        self.assertIn("data.append('composer_context', this.context)", controller)
        self.assertIn("input.value.slice(0, start) + proposal + this.input.value.slice(start)", controller)
        self.assertIn("utf16Length(combined) > this.maxLength", controller)
        self.assertIn("Record again", controller)
        self.assertIn("Not now", controller)
        self.assertIn("Retry", controller)
        self.assertIn("Enable microphone", controller)
        self.assertIn("communityVoiceRetry.request(fetch", controller)
        self.assertNotIn("api('/api/v1/community/voice/transcriptions'", controller)
        self.assertIn("this.retryState", controller)
        self.assertIn("communityVoiceRetry.RETRY_TTL_MS", controller)
        self.assertIn("this.retryState, 'expiry'", controller)
        self.assertIn("this.retryState, 'retry'", controller)
        self.assertIn("voiceOwnsFocus", controller)
        self.assertIn("if (!this.panel.isConnected)", controller)
        self.assertIn("requestGeneration !== self.requestGeneration", controller)
        self.assertIn("if (self.cancelled || self.state !== 'permission') return;", controller)
        self.assertNotIn("localStorage", controller)
        self.assertNotIn("requestSubmit", controller)
        self.assertNotIn("sendPrimaryComment", controller)
        self.assertIn("pagehide", self.script)
        self.assertIn("visibilitychange", self.script)
        self.assertIn("pageshow", self.script)
        self.assertIn("new CommunityVoiceController({", self.script)
        self.assertIn("context: 'post'", self.script)
        self.assertIn("maxLength: 4000", self.script)
        self.assertIn("noun: 'post'", self.script)
        self.assertIn("context: 'contribution'", self.script)
        self.assertIn("maxLength: 2000", self.script)
        self.assertIn("noun: 'reply'", self.script)
        self.assertIn("lifetime: 'feed'", self.script)
        self.assertIn("lifetime: 'page'", self.script)
        self.assertIn("mirrors: topTrigger ? [topTrigger] : []", self.script)
        self.assertIn("if (composerVoiceController) composerVoiceController.discard(false);", self.script)
        self.assertIn("if (replyVoiceController) replyVoiceController.discard(false);", self.script)
        self.assertIn("Finish or discard the Voice review before continuing.", self.script)
        self.assertIn("data-top-voice", self.template)
        self.assertIn("data-composer-voice", self.template)
        self.assertIn("data-reply-voice", self.template)
        self.assertIn("data-composer-voice-panel-host", self.template)
        self.assertIn("data-reply-voice-panel-host", self.template)
        self.assertIn("data-reply-attachment-input", self.template)
        self.assertNotIn("data-voice-unavailable", self.template)
        self.assertIn("cv1-comment-voice-panel", self.styles)
        reduced_motion = self.styles[self.styles.index("@media (prefers-reduced-motion: reduce)"):]
        self.assertIn("animation-duration: .01ms", reduced_motion)
        self.assertIn("animation-iteration-count: 1", reduced_motion)
        self.assertIn("transition-duration: .01ms", reduced_motion)
        self.assertIn("cv1-voice-control.cv1-secondary", self.styles)
        self.assertIn("background: #10243c; color: #b9d3ff", self.styles)
        self.assertIn("Speech transcription provider", self.policy)

    def test_focused_node_retry_lifecycle_contract(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is unavailable.")
        completed = subprocess.run(
            [node, str(ROOT / "tests" / "community_voice_retry.test.js")],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )

    def test_voice_propagation_keeps_existing_send_boundaries_and_scoped_lifetimes(self):
        # PS-COMMUNITY-AUTH-WALL-001: the signed-out demo Voice instance is
        # retired, leaving the three real owner controllers (primary comment,
        # composer, reply).
        self.assertEqual(self.script.count("new CommunityVoiceController({"), 3)
        self.assertIn("context: 'post'", self.script)
        self.assertIn("context: 'contribution'", self.script)
        self.assertIn("maxLength: 4000", self.script)
        self.assertIn("maxLength: 2000", self.script)
        self.assertIn("openComposer('post', null, false);", self.script)
        self.assertIn("composerVoiceController.start();", self.script)
        self.assertIn("disposeCommunityVoiceControllers('feed')", self.script)
        self.assertIn("if (!lifetime || controller.lifetime === lifetime) controller.dispose();", self.script)
        self.assertIn("if (conversation.open && replyVoiceController) {", self.script)
        self.assertIn("saveReplyDraft();\n      replyVoiceController.discard(false);", self.script)
        self.assertIn("if (replyVoiceController) replyVoiceController.discard(false);", self.script)
        self.assertIn("if (composerVoiceController) composerVoiceController.discard(false);", self.script)
        # No shipped controller opts into the local-only demo mode anymore;
        # localOnly survives only as a capability of the controller itself.
        self.assertNotIn("localOnly: !owner", self.script)
        self.assertNotIn("localOnly: demo", self.script)
        self.assertNotIn("there is deliberately no Publish button", self.template)
        controller = self.script[
            self.script.index("function CommunityVoiceController"):
            self.script.index("function resizePrimaryComment")
        ]
        self.assertNotIn("requestSubmit", controller)
        self.assertNotIn("submitComposerMutation", controller)
        self.assertNotIn("sendReply", controller)

    def test_post_edit_hides_attachment_controls_without_hiding_voice(self):
        self.assertIn(
            '<div class="cv1-composer-tool-strip" aria-label="Post tools">',
            self.template,
        )
        self.assertNotIn(
            'aria-label="Post tools" data-composer-attachment-control',
            self.template,
        )
        self.assertEqual(self.template.count("data-composer-attachment-control"), 3)
        self.assertIn("data-composer-voice", self.template)
        self.assertIn(
            "app.querySelectorAll('[data-composer-attachment-control]')",
            self.script,
        )
        helper = self.script[
            self.script.index("function composerVoiceReadyForSubmission"):
            self.script.index("function openPublicConfirmation")
        ]
        self.assertIn("hasUnresolvedVoice()", helper)
        self.assertIn("composerVoiceController.focusTrigger()", helper)
        confirmation = self.script[
            self.script.index("function openPublicConfirmation"):
            self.script.index("function closePublicConfirmation")
        ]
        mutation = self.script[
            self.script.index("function submitComposerMutation"):
            self.script.index("function publish")
        ]
        self.assertIn("composerVoiceReadyForSubmission()", confirmation)
        self.assertIn("composerVoiceReadyForSubmission()", mutation)


if __name__ == "__main__":
    unittest.main()
