import pathlib
import re
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
        # PS-VOICE-VISUAL-PARITY-001 (2026-07-19, owner-approved revision):
        # the Voice recording/review overlay portals to <body> and uses
        # position: fixed for its full-viewport backdrop only, because
        # main.main-content's isolation:isolate establishes a stacking
        # context that otherwise traps a nested fixed overlay below the
        # sticky global header (verified against templates/base.html and
        # static/css/style.css, not merely asserted). Every other Voice/
        # Capture rule must stay in normal, non-fixed document flow.
        fixed_rule_selectors = re.findall(r"([^{}]+)\{[^{}]*position:\s*fixed[^{}]*\}", STYLES)
        self.assertTrue(
            fixed_rule_selectors,
            "expected the Voice overlay backdrop rule to use position: fixed",
        )
        for selector in fixed_rule_selectors:
            self.assertIn(
                "voice-backdrop",
                selector,
                "position: fixed must stay scoped to the Voice overlay backdrop, "
                f"found on: {selector.strip()}",
            )

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
        self.assertIn("animation: none !important", STYLES)

    def test_voice_and_type_are_first_class_opening_choices_without_auto_modal(self):
        # Manager point 2 (06_VISUAL_PARITY_CORRECTION.md): both Speak and Type
        # appear before any modal opens; choosing Speak opens the Voice modal;
        # the Voice modal is never auto-opened on ordinary page load.
        self.assertIn('data-capture-mode="text"', TEMPLATE)
        self.assertIn('data-capture-mode="voice"', TEMPLATE)
        # The prior auto-open on load is removed.
        self.assertNotIn('switchMode("voice", false)', CLIENT)
        self.assertNotIn("if (!reviewStage) switchMode", CLIENT)
        # A mode button click switches mode; the voice path portals a modal.
        self.assertIn("switchMode(button.dataset.captureMode)", CLIENT)
        self.assertIn("portalIn(", CLIENT)

    def test_capability_previews_are_genuinely_disabled_and_labeled(self):
        # PS-VOICE-VISUAL-PARITY-001: future affordances (Community,
        # Connections, Selected people, My Story, Slate Board, Resume,
        # Photo/Video/Document, AI wording) are visible per the approved
        # walkthrough composition, but must be real, non-operable HTML
        # controls carrying a truthful "Coming later" label, not disguised
        # working buttons.
        for label in ("Connections", "Community", "Selected people", "My Story", "Slate Board"):
            self.assertIn(label, TEMPLATE)
        self.assertIn("R&eacute;sum&eacute;", TEMPLATE)
        self.assertGreaterEqual(TEMPLATE.count("Coming later"), 8)
        self.assertGreaterEqual(TEMPLATE.count('disabled aria-disabled="true"'), 6)
        self.assertIn('<input type="radio" name="audience_preview" checked disabled', TEMPLATE)
        self.assertIn("AI-assisted wording", TEMPLATE)
        self.assertIn("coming later", TEMPLATE)
        self.assertIn(
            "Your original transcript will always remain unchanged",
            TEMPLATE,
        )
        self.assertIn("Publishing and audience choices are coming later.", TEMPLATE)

    def test_review_states_explicit_private_status(self):
        self.assertIn("This Capture is private and visible only to you.", TEMPLATE)

    def test_dialog_semantics_are_managed_by_js_not_static_markup(self):
        # Manager point 5: dialog/aria-modal semantics belong to the modal
        # presentation. They are added by JS on portal and removed on Close, so
        # the same section rendered inline (no-JS, or after Close) is not
        # falsely announced as a modal dialog.
        self.assertNotIn('role="dialog"', TEMPLATE)
        self.assertNotIn('aria-modal="true"', TEMPLATE)
        self.assertIn('setAttribute("role", "dialog")', CLIENT)
        self.assertIn('setAttribute("aria-modal", "true")', CLIENT)
        self.assertIn('removeAttribute("role")', CLIENT)
        self.assertIn('removeAttribute("aria-modal")', CLIENT)
        # Still portals to a body-level root, traps focus, and closes on Escape.
        self.assertIn("voice-overlay-root", CLIENT)
        self.assertIn("document.body.appendChild(overlayRoot)", CLIENT)
        self.assertIn('event.key === "Escape"', CLIENT)
        self.assertIn("trapFocus", CLIENT)

    def test_background_inert_and_focus_restore_to_invoker(self):
        # Manager point 5: page background inert/aria-hidden while a modal is
        # open, and focus restored to the invoker (the Speak button) on close.
        self.assertIn("setBackgroundInert", CLIENT)
        self.assertIn('setAttribute("inert", "")', CLIENT)
        self.assertIn('setAttribute("aria-hidden", "true")', CLIENT)
        self.assertIn("restoreFocus", CLIENT)
        self.assertIn("voiceModeButton", CLIENT)

    def test_gold_save_reassurance_and_persistent_footer(self):
        # Manager point 3: Save private Capture uses the approved gold emphasis
        # (text-safe strong gold #8A5A00) in light and dark; it is the only
        # action with the gold modifier — other primaries stay navy.
        self.assertIn("owner-app__voice-save", TEMPLATE)
        self.assertIn(".owner-app__voice-save", STYLES)
        self.assertIn("#8a5a00", STYLES)
        self.assertIn('body[data-theme="dark"] .owner-app__voice-save', STYLES)
        # Manager point 4: the non-destructive-close reassurance is visible.
        self.assertIn(
            "Close keeps your private draft; resume any time from this page.",
            TEMPLATE,
        )
        # Manager point 6: the Save footer is pinned by the flex-column modal
        # layout (not discoverable below the fold); its controls associate with
        # the review form by id so the delete form is never nested.
        self.assertIn(".owner-app__voice-backdrop .owner-app__voice-review-footer", STYLES)
        self.assertIn("owner-app__voice-review-scroll", STYLES)
        self.assertIn('form="voice-confirm-form"', TEMPLATE)
        self.assertIn("Save private Capture", TEMPLATE)

    def test_focus_trap_accounts_for_summary_and_content_visibility(self):
        # The focus trap must count <summary> elements (keyboard-focusable but
        # matched by no ordinary control selector) and must NOT count content
        # inside a closed <details> (hidden via content-visibility, which
        # offsetParent does not reflect). Otherwise the modal leaks focus.
        self.assertIn("summary", CLIENT)
        self.assertIn("checkVisibility", CLIENT)
        self.assertIn("contentVisibilityAuto", CLIENT)
        # A purposeful initial focus target is declared on both dialogs.
        self.assertEqual(TEMPLATE.count("data-autofocus"), 2)

    def test_mobile_progressive_disclosure_and_pinned_save(self):
        self.assertIn('<details class="owner-app__voice-more" open>', TEMPLATE)
        self.assertIn("More ways to use this", TEMPLATE)
        self.assertIn(".owner-app__voice-review-footer {", STYLES)
        # The Save footer is pinned by the flex-column modal layout, so it stays
        # visible while the review body scrolls (no position: sticky needed).
        self.assertIn(".owner-app__voice-backdrop .owner-app__voice-review-footer", STYLES)
        self.assertIn("flex: 0 0 auto", STYLES)


if __name__ == "__main__":
    unittest.main()
