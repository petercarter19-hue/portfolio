import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "owner_capture.html").read_text(encoding="utf-8")
CLIENT = (ROOT / "static" / "js" / "owner-capture-voice.js").read_text(encoding="utf-8")
STYLES = (ROOT / "static" / "css" / "owner-app.css").read_text(encoding="utf-8")


class OwnerVoiceUiContractTests(unittest.TestCase):
    def test_permission_is_requested_only_after_explicit_start(self):
        self.assertIn('data-voice-action="start"', TEMPLATE)
        self.assertIn('addEventListener("click", startRecording)', CLIENT)
        self.assertIn("getUserMedia", CLIENT)
        self.assertIn("Microphone access has not been requested", TEMPLATE)

    def test_failure_unsupported_and_denied_states_keep_text_fallback(self):
        for phrase in (
            "not supported in this browser",
            "Microphone access was denied or unavailable",
            "You appear to be offline",
            "Switch to Type",
        ):
            self.assertIn(phrase, TEMPLATE + CLIENT)
        self.assertIn("Text Capture is always available", TEMPLATE)

    def test_limits_cancel_double_submit_and_status_announcements_are_present(self):
        for contract in (
            "20971520",
            "180",
            "cancelled",
            "submitting",
            'role="status"',
            'aria-live="polite"',
        ):
            self.assertIn(contract, TEMPLATE + CLIENT)

    def test_review_distinguishes_provider_text_and_explicit_private_save(self):
        for contract in (
            "original provider transcript",
            "provenance record is immutable",
            "Reviewed Capture text",
            "Save private Capture",
            "Do not share or publish it",
        ):
            self.assertIn(contract, TEMPLATE)

    def test_uploaded_but_unqueued_source_can_be_retried_or_deleted(self):
        self.assertIn("The private audio is stored, but transcription has not started", TEMPLATE)
        self.assertIn("voice_draft.state in ['uploading', 'queued', 'processing']", TEMPLATE)
        self.assertIn("voice_draft.state == 'failed' and voice_draft.attempt_number", TEMPLATE)
        self.assertIn("Retry transcription", TEMPLATE)

    def test_failed_upload_without_attempt_has_truthful_fallback_only(self):
        self.assertIn("This upload cannot be retried", TEMPLATE)
        self.assertIn("Record again", TEMPLATE)
        self.assertIn("Switch to Type", TEMPLATE)

    def test_mobile_focus_reduced_motion_and_document_flow_are_scoped(self):
        self.assertIn("@media (max-width: 540px)", STYLES)
        self.assertIn("@media (prefers-reduced-motion: reduce)", STYLES)
        self.assertIn(":focus-visible", STYLES)
        self.assertIn("resize: vertical", STYLES)
        self.assertNotIn("position: fixed", STYLES)

    def test_homepage_voice_authority_is_reflected_without_faking_behavior(self):
        for contract in (
            ">Type</button>",
            ">Speak</button>",
            "Say what happened.",
            "What happened today that you may want to remember?",
            "data-voice-wave",
            "owner-voice-listening",
        ):
            self.assertIn(contract, TEMPLATE + STYLES)
        self.assertIn('data-voice-state="recording"', STYLES)
        self.assertIn('"recording"', CLIENT)
        self.assertIn('switchMode("voice", false)', CLIENT)
        self.assertIn("animation: none !important", STYLES)


if __name__ == "__main__":
    unittest.main()
