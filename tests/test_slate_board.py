import re
import unittest
from pathlib import Path

from app import app


class SlateBoardLivingWhiteboardTests(unittest.TestCase):
    """Lock the Photo 1 living-whiteboard baseline and its trust boundaries."""

    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        self.original_database_ui = app.config.get("PEERSLATE_DATABASE_UI_ENABLED")
        self.original_allow_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        self.original_dev_user_key = app.config.get("PEERSLATE_DEV_USER_KEY")
        app.config.update(
            TESTING=True,
            PEERSLATE_DATABASE_UI_ENABLED=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(
            TESTING=self.original_testing,
            PEERSLATE_DATABASE_UI_ENABLED=self.original_database_ui,
            PEERSLATE_ALLOW_DEV_IDENTITY=self.original_allow_dev_identity,
            PEERSLATE_DEV_USER_KEY=self.original_dev_user_key,
        )

    def board_html(self, path="/petec/slate-board"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_both_routes_render_the_photo_one_workspace(self):
        for path in ("/slate-board", "/petec/slate-board"):
            with self.subTest(path=path):
                html = self.board_html(path)
                self.assertIn('class="global-header"', html)
                self.assertIn('slate-board-living-whiteboard', html)
                self.assertIn('data-board-root', html)
                self.assertIn('class="sb-workspace"', html)
                self.assertIn('<h1 id="slate-board-title">Slate Board</h1>', html)
                self.assertIn('<p>Executive Planning Wall</p>', html)
                self.assertIn('<span>Sharing</span>', html)
                self.assertIn('class="sb-icon-button sb-header-more"', html)
                self.assertIn('v=consolidated-slate-1', html)

                self.assertNotIn('Capture ideas. Plan your future. Take action.', html)
                self.assertNotIn('What We\'re Tracking', html)
                self.assertNotIn('class="sb-hero"', html)

    def test_left_control_rail_matches_the_reference_without_claiming_live_presence(self):
        html = self.board_html()
        self.assertIn('<aside class="sb-controls" aria-label="Board controls">', html)
        for label in (
            'Board controls',
            'Add to Board',
            'Select',
            'Undo',
            'Redo',
            'View',
            'Fit to view',
            'List view',
        ):
            self.assertIn(label, html)

        self.assertIn('Private working board', html)
        self.assertIn('data-save-status', html)
        self.assertIn('Today on your Slate', html)
        self.assertIn('Log today’s progress', html)
        self.assertIn('Paths &amp; milestones', html)
        self.assertNotIn('Connections preview <span>(4)</span>', html)
        self.assertNotIn('Presence preview only', html)
        self.assertNotIn('<span>Add note</span>', html)
        self.assertNotIn('<span>Draw</span>', html)
        self.assertNotIn('Participants (4)', html)
        self.assertNotIn('All caught up', html)

    def test_board_has_the_physical_reference_objects_and_four_product_sections(self):
        html = self.board_html()

        self.assertIn('class="sb-frame"', html)
        self.assertEqual(html.count('class="sb-frame__corner '), 4)
        self.assertIn('class="sb-enamel-sheen"', html)
        self.assertIn('class="sb-board-sketches"', html)
        self.assertIn('class="sb-marker-tray" aria-label="Marker tray and board shortcuts"', html)
        self.assertIn('class="sb-marker sb-marker--ink"', html)
        self.assertIn('class="sb-marker sb-marker--blue"', html)
        self.assertIn('class="sb-marker sb-marker--red"', html)
        self.assertIn('class="sb-eraser"', html)
        self.assertIn('<strong>PeerSlate</strong>', html)
        self.assertIn('class="sb-reference-footer"', html)

        expected_sections = {
            'short': 'Short Term',
            'projects': 'Projects',
            'long': 'Long Term',
            'work': 'Work',
        }
        self.assertEqual(html.count('data-column="'), 4)
        self.assertEqual(html.count('<h2 class="sb-column__heading"'), 4)
        for section, label in expected_sections.items():
            self.assertIn(f'data-column="{section}"', html)
            self.assertIn(f'data-note-list="{section}"', html)
            self.assertIn(f'aria-controls="sb-list-{section}"', html)
            self.assertIn(f'<span class="sb-column__title">{label}</span>', html)

        seed_notes = re.findall(r'<article\s+class="sb-note(?:\s|")', html)
        self.assertEqual(len(seed_notes), 20)
        self.assertIn('Study for the PMP certification', html)
        self.assertIn('Complete two practice exams', html)
        self.assertIn('Review the plan with Danielle', html)
        self.assertNotIn('data-column="todo"', html)
        self.assertNotIn('data-column="someday"', html)

    def test_chalk_it_up_is_capture_then_review_then_explicit_private_approval(self):
        html = self.board_html()
        javascript = Path('static/js/slate-board.js').read_text(encoding='utf-8')

        self.assertIn('id="sb-capture-form"', html)
        self.assertIn('<h2 id="sb-capture-title">Chalk It Up</h2>', html)
        self.assertIn('for="sb-capture-transcript">Type or edit your private capture', html)
        self.assertIn('data-capture-listen>Preview listening state', html)
        self.assertIn('type="submit" data-capture-review>Review draft', html)
        self.assertIn('Private draft. Nothing has been saved or shared yet.', html)

        self.assertIn('data-proposal-panel', html)
        self.assertIn('Review what PeerSlate understood', html)
        self.assertRegex(
            html,
            r'name="proposalAudience" value="private" checked',
        )
        self.assertRegex(
            html,
            r'name="proposalAudience" value="share" disabled',
        )
        self.assertRegex(
            html,
            r'name="proposalAudience" value="publish" disabled',
        )
        self.assertIn('data-approve-proposals>Approve private items', html)
        self.assertIn(
            'It does not invoke AI, send invitations, or publish records.',
            html,
        )

        self.assertIn('function buildProposals(text)', javascript)
        self.assertIn('function approveProposals()', javascript)
        self.assertIn("canSave: false", javascript)
        self.assertIn('No invitation will be sent.', javascript)
        self.assertIn('No relationship was invited or published.', javascript)

    def test_sharing_states_are_honest_and_do_not_offer_false_send_or_publish_actions(self):
        html = self.board_html()
        javascript = Path('static/js/slate-board.js').read_text(encoding='utf-8')

        self.assertIn('<h2 id="sb-share-title">Sharing is not connected yet</h2>', html)
        self.assertIn('Default. Changes remain in this browser.', html)
        self.assertIn('Requires the protected sharing service.', html)
        self.assertIn('Not connected', html)
        self.assertIn(
            'No invitations, access grants, or publishing occur from this page.',
            html,
        )
        self.assertNotIn('>Send invitation</button>', html)
        self.assertNotIn('>Publish board</button>', html)
        self.assertNotIn('sb-invite-form', html)
        self.assertNotIn('function addCollaborator()', javascript)

    def test_note_editor_preserves_taxonomy_and_private_defaults(self):
        html = self.board_html()
        self.assertIn('id="sb-note-dialog"', html)
        self.assertIn('id="sb-note-form"', html)
        self.assertIn('id="sb-note-title" name="title" type="text" maxlength="120" required', html)

        for value, label in (
            ('short', 'Short Term'),
            ('projects', 'Projects'),
            ('long', 'Long Term'),
            ('work', 'Work'),
        ):
            self.assertIn(f'<option value="{value}">{label}</option>', html)

        for item_type in ('To Do', 'Short Term', 'Long Term', 'Project', 'Work', 'Custom'):
            self.assertIn(f'<option value="{item_type}">', html)

        self.assertIn('Sticky-note color', html)
        self.assertIn('Date or timeline', html)
        self.assertIn('Private by default', html)
        self.assertIn('The filename is remembered here; the file itself is never uploaded.', html)

    def test_list_view_and_mobile_accordion_are_equivalent_accessible_paths(self):
        html = self.board_html()
        css = Path('static/css/slate-board.css').read_text(encoding='utf-8')
        javascript = Path('static/js/slate-board.js').read_text(encoding='utf-8')

        self.assertIn('data-board-view-state="board"', html)
        self.assertIn('data-toggle-board-view aria-pressed="false"', html)
        self.assertEqual(html.count('data-column-toggle'), 4)
        self.assertEqual(html.count('aria-expanded="true" aria-controls="sb-list-'), 4)
        self.assertIn('role="checkbox"', html)
        self.assertIn('draggable="true"', html)
        self.assertIn('aria-live="polite"', html)

        self.assertIn('.sb-workspace.is-list-view', css)
        self.assertIn('@media (max-width: 759px)', css)
        self.assertIn(
            '.sb-workspace.is-enhanced .sb-column:not(.is-open) .sb-note-list',
            css,
        )
        self.assertIn('function setBoardView(view, trigger, silent)', javascript)
        self.assertIn('function applyResponsiveColumns()', javascript)
        self.assertIn('function toggleMobileColumn(column)', javascript)
        self.assertIn("var SECTION_ORDER = ['short', 'projects', 'long', 'work'];", javascript)
        self.assertIn("window.matchMedia('(max-width: 759px)')", javascript)
        self.assertIn("event.altKey && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')", javascript)

    def test_photo_one_style_lock_includes_physical_depth_and_accessibility_modes(self):
        css = Path('static/css/slate-board.css').read_text(encoding='utf-8')

        self.assertIn('Photo 1 visual lock', css)
        self.assertIn('width: min(100%, 1500px);', css)
        self.assertRegex(css, r'(?s)\.sb-stage\s*\{[^}]*grid-template-columns:')
        self.assertRegex(css, r'(?s)\.sb-frame\s*\{[^}]*aspect-ratio:')
        self.assertIn('.sb-frame__corner', css)
        self.assertIn('.sb-enamel-sheen', css)
        self.assertIn('.sb-marker-tray', css)
        self.assertIn('.sb-marker--red', css)
        self.assertIn('.sb-eraser', css)
        self.assertIn('.sb-reference-footer', css)
        self.assertIn('font-family: Caveat', css)

        self.assertIn('@media (max-width: 759px)', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('@media (forced-colors: active)', css)
        self.assertIn('.sb-page :focus-visible', css)

    def test_storage_copy_remains_honest_for_all_feature_flag_states(self):
        browser_preview = self.board_html()
        self.assertIn('data-board-api="false"', browser_preview)
        self.assertIn('data-board-storage-scope="petec-preview"', browser_preview)
        self.assertIn('stores changes only in this browser', browser_preview)

        app.config.update(
            PEERSLATE_DATABASE_UI_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY='slate-board-test-user',
        )
        database_preview = self.board_html()
        self.assertIn('data-board-api="true"', database_preview)
        self.assertRegex(database_preview, r'data-board-storage-scope="member-[a-f0-9]{20}"')
        self.assertIn('Your authenticated private Slate Board is loaded.', database_preview)
        self.assertIn('Saved privately', database_preview)

        app.config.update(
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )
        signed_out_preview = self.board_html()
        self.assertIn('data-board-api="false"', signed_out_preview)
        self.assertIn('data-board-storage-scope="signed-out"', signed_out_preview)
        self.assertIn('stores changes only in this browser', signed_out_preview)


if __name__ == '__main__':
    unittest.main()
