"""Contracts for the Pete-locked Community authoring runtime candidate."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "initiatives" / "PS-COMMUNITY-AUTHORING-RUNTIME-001"
VISUAL_LOCK = (
    ROOT
    / "docs"
    / "initiatives"
    / "PS-COMMUNITY-VISUAL-REFINEMENT-001"
    / "visual-authority"
    / "2026-08-17-pete-lock"
)


class CommunityAuthoringRuntimeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "community_feed.html").read_text(encoding="utf-8")
        cls.styles = (ROOT / "static" / "css" / "community-v1.css").read_text(encoding="utf-8")
        cls.script = (ROOT / "static" / "js" / "community-v1.js").read_text(encoding="utf-8")
        cls.routes = (ROOT / "community_routes.py").read_text(encoding="utf-8")
        cls.api = (ROOT / "community_api.py").read_text(encoding="utf-8")
        cls.architecture = (PACKAGE / "00_ARCHITECTURE.md").read_text(encoding="utf-8")

    def test_exact_visual_authority_is_present(self):
        self.assertEqual(
            [path.name for path in sorted(VISUAL_LOCK.iterdir()) if path.is_file()],
            [
                "01_desktop_mine_ours_beyond_structure.png",
                "02_desktop_composer_active_geometry.png",
                "03_desktop_composer_empty_geometry.png",
                "04_desktop_audience_menu_geometry.png",
                "05_desktop_voice_and_color_authority.jpg",
                "06_authoring_state_sheet.jpg",
                "07_published_post_and_replies.jpg",
                "08_ipad_landscape_composer.jpg",
                "09_mobile_ordinary_composer.jpg",
                "10_accessibility_responsive_board.jpg",
            ],
        )

    def test_architecture_preserves_the_current_authorization_boundary(self):
        prose = " ".join(self.architecture.split())
        self.assertIn("does not expand author eligibility", self.architecture)
        self.assertIn("current owner-authoring pilot", self.architecture)
        self.assertIn("other signed-in members receive the read-only Community surface", prose)
        self.assertIn('owner = bool(identity and is_owner(identity))', self.routes)
        self.assertIn('if not context["community_owner"]:', self.routes)
        self.assertIn("if not is_owner(identity):", self.api)

    def test_mine_ours_beyond_replaces_spark_as_the_page_model(self):
        for view in ("mine", "ours", "beyond"):
            self.assertIn(f'data-community-view="{view}"', self.template)
        self.assertIn('data-community-view="ours" aria-pressed="true"', self.template)
        self.assertIn("setMobileCommunityView('ours')", self.script)
        self.assertNotIn("Use this Spark", self.template)
        self.assertNotIn("data-spark-prompt", self.template)
        self.assertIn("**Spark:** absent", self.architecture)

    def test_audience_menu_is_compact_truthful_and_non_reflowing(self):
        self.assertIn('<option value="public">Community</option>', self.template)
        self.assertIn('role="listbox" aria-label="Choose audience"', self.template)
        self.assertIn("Draft only in this release", self.template)
        self.assertIn("Connections are not available yet.", self.template)
        self.assertIn('data-audience-choice="public"', self.template)
        self.assertIn("Signed-in PeerSlate members", self.template)
        self.assertIn("Public posting is not available yet.", self.template)
        self.assertIn("width: 220px", self.styles)
        self.assertIn("position: absolute", self.styles)

    def test_tools_are_icon_only_and_use_semantic_accents(self):
        photo = self.template.index("cv1-composer-tool--photo")
        video = self.template.index("cv1-composer-tool--video", photo)
        file_tool = self.template.index("cv1-composer-tool--file", video)
        voice = self.template.index("cv1-composer-tool--voice", file_tool)
        ai = self.template.index("cv1-composer-tool--ai", voice)
        self.assertLess(photo, video)
        self.assertLess(video, file_tool)
        self.assertLess(file_tool, voice)
        self.assertLess(voice, ai)
        for token in ("photo", "video", "file", "voice", "ai"):
            self.assertIn(f"--community-accent-{token}:", self.styles)
        self.assertIn('aria-label="Add video — not yet available"', self.template)
        self.assertIn('aria-disabled="true"', self.template)

    def test_published_feed_uses_compact_media_private_save_and_reply_previews(self):
        self.assertIn("cv1-attachment-image-copy", self.script)
        self.assertIn("grid-template-columns: 112px minmax(0, 1fr)", self.styles)
        self.assertIn("function postSaveControl(post)", self.script)
        self.assertIn("function performPostSave(control, post)", self.script)
        self.assertIn("saved ? 'Saved privately' : 'Save privately'", self.script)
        self.assertIn("'/save'", self.script)
        self.assertIn(".cv1-card-actions--primary .cv1-action-count { display: none; }", self.styles)
        self.assertIn("cv1-reply-preview-avatar", self.script)
        self.assertIn("cv1-reply-preview-copy", self.script)
        self.assertIn("[data-conversation-shelf-track] > li:nth-child(n + 4) { display: none; }", self.styles)

    def test_ai_is_an_honest_unavailable_proposal_surface(self):
        for action in ("Make clearer", "Make shorter", "Ask a better question"):
            self.assertIn(action, self.template)
        self.assertEqual(self.template.count('role="menuitem" aria-disabled="true" data-ai-unavailable'), 3)
        self.assertIn("Your original stays unchanged. AI proposals are not enabled yet.", self.template)
        self.assertIn("AI writing proposals are not enabled yet. Your original is unchanged.", self.script)
        self.assertIn("This package will not fake", self.architecture)

    def test_composer_is_compact_white_and_grows_within_bounds(self):
        self.assertIn("width: min(540px, calc(100vw - 32px))", self.styles)
        self.assertIn("height: fit-content", self.styles)
        self.assertIn("background: #fff", self.styles)
        self.assertIn("Math.max(92, Math.min(editor.scrollHeight, 240))", self.script)
        self.assertIn("composer.showModal()", self.script)
        self.assertNotIn("composer.show();", self.script)
        self.assertIn("Not saved yet", self.template)
        self.assertIn("Saved privately", self.script)

    def test_hidden_native_selects_submit_without_joining_keyboard_order(self):
        self.assertIn(
            'name="audience" required aria-label="Post audience" tabindex="-1"',
            self.template,
        )
        self.assertIn('name="response_posture" required tabindex="-1"', self.template)
        self.assertNotIn('name="audience" disabled', self.template)
        self.assertNotIn('name="response_posture" disabled', self.template)

    def test_phone_publication_confirmation_overrides_full_height_dialog_rules(self):
        responsive_confirmation = self.styles[
            self.styles.index(
                "@media (max-width: 700px), (max-height: 520px) and (max-width: 950px)"
            ) :
        ]
        self.assertIn(
            ".cv1-dialog.cv1-public-confirmation:not(.cv1-activity-dialog):not(.cv1-catchup-dialog) {",
            responsive_confirmation,
        )
        self.assertIn("width: min(360px, calc(100vw - 32px))", responsive_confirmation)
        self.assertIn("height: fit-content", responsive_confirmation)
        self.assertIn("margin: auto", responsive_confirmation)
        self.assertIn(
            ".cv1-dialog.cv1-public-confirmation:not(.cv1-activity-dialog):not(.cv1-catchup-dialog) .cv1-dialog-frame",
            responsive_confirmation,
        )
        self.assertIn("height: auto", responsive_confirmation)

    def test_beyond_rail_uses_truthful_empty_states(self):
        self.assertIn("No active questions to show.", self.template)
        self.assertIn("member-backed results are available", self.template)
        self.assertIn("No recommendations yet.", self.template)
        self.assertIn("member-backed recommendations are available", self.template)
        self.assertNotIn(
            "How do you structure a handoff for complex systems work?", self.template
        )
        self.assertNotIn(
            "Recommended tools for requirements traceability?", self.template
        )
        self.assertNotIn("A practical handoff checklist", self.template)

    def test_editor_recalculates_after_create_and_edit_composers_open(self):
        helper = "function recalculateEditorAfterComposerOpen()"
        self.assertIn(helper, self.script)
        self.assertIn("window.requestAnimationFrame(function ()", self.script)
        self.assertIn("window.requestAnimationFrame(updateCount)", self.script)
        self.assertEqual(self.script.count("recalculateEditorAfterComposerOpen();"), 2)
        create = self.script[self.script.index("function openComposer(") : self.script.index("function openEdit(")]
        edit = self.script[self.script.index("function openEdit(") : self.script.index("function uploadStateLabel(")]
        for flow in (create, edit):
            self.assertLess(flow.index("presentComposer();"), flow.index("recalculateEditorAfterComposerOpen();"))

    def test_successful_edit_preserves_the_unrelated_create_draft(self):
        helper = self.script[
            self.script.index("function clearCreateDraftAfterSuccessfulMutation(") :
            self.script.index("function submitComposerMutation(")
        ]
        self.assertIn("if (editing) return;", helper)
        self.assertIn("localStorage.removeItem(draftKey);", helper)
        self.assertIn("localStorage.removeItem(postCommandStorageKey);", helper)
        submit_start = self.script.index("function submitComposerMutation(")
        success_start = self.script.index("request.then(function ()", submit_start)
        success = self.script[
            success_start : self.script.index("state.cursor = null;", success_start)
        ]
        self.assertIn("clearCreateDraftAfterSuccessfulMutation(editing);", success)
        self.assertIn("closeComposer({saveDraft: false});", success)
        self.assertIn("finalizeComposerDraftAfterClose();", self.script)

    def test_901_to_1288_rail_override_remains_intact(self):
        hide_rule = self.styles.index("@media (max-width: 1288px)")
        later_override = self.styles.index(".cv1-rail {\n  display: block;", hide_rule)
        self.assertGreater(later_override, hide_rule)

    def test_mobile_is_an_ordinary_bottom_sheet_not_a_default_full_screen(self):
        self.assertIn("@media (max-width: 700px)", self.styles)
        self.assertIn("inset: auto 0 0", self.styles)
        self.assertIn("height: min(72dvh, 720px)", self.styles)
        self.assertIn("padding-bottom: env(safe-area-inset-bottom)", self.styles)
        self.assertIn("@media (max-height: 620px)", self.styles)

    def test_accessibility_modes_and_focus_restoration_are_explicit(self):
        self.assertIn("@media (forced-colors: active)", self.styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.styles)
        self.assertIn("composerReturnFocus", self.script)
        self.assertIn("focus({preventScroll: true})", self.script)
        self.assertIn("closeAudienceMenu(true)", self.script)
        self.assertIn("closeAiMenu(true)", self.script)

    def test_search_entry_reveals_the_control_before_focus(self):
        handler = self.script[self.script.index("app.querySelector('[data-search-questions]')") :]
        self.assertLess(
            handler.index("document.body.classList.add('community-search-active')"),
            handler.index("searchInput.focus()"),
        )
        self.assertIn("body.community-search-active .cv1-toolbar", self.styles)


if __name__ == "__main__":
    unittest.main()
