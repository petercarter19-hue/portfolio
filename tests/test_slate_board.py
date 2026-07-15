import unittest
from pathlib import Path

from app import app


class SlateBoardRedesignTests(unittest.TestCase):
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

    def test_both_routes_render_the_single_redesigned_workspace(self):
        for path in ("/slate-board", "/petec/slate-board"):
            with self.subTest(path=path):
                html = self.board_html(path)
                self.assertIn('data-board-root', html)
                self.assertIn('class="sb-workspace"', html)
                self.assertIn('<h1 id="slate-board-title">Slate Board</h1>', html)
                self.assertIn('Capture ideas. Plan your future. Take action.', html)
                self.assertNotIn('My Whiteboard', html)
                self.assertNotIn('Chalk It Up', html)
                self.assertNotIn('What We\'re Tracking', html)

    def test_seed_board_matches_the_four_column_concept(self):
        html = self.board_html()
        self.assertEqual(html.count('data-note-id='), 14)

        expected = {
            'data-column="todo"': ('To Do', 'Finish system design', 'Call Mom'),
            'data-column="short"': ('Short Term', 'Launch new portfolio site', 'Run a half marathon'),
            'data-column="long"': ('Long Term', 'Financial independence', 'Write a book'),
            'data-column="someday"': ('Someday', 'Travel the world', 'Live off the grid'),
        }
        for marker, content in expected.items():
            self.assertIn(marker, html)
            for text in content:
                self.assertIn(text, html)

        board_columns = html.split('<div class="sb-columns"', 1)[1].split(
            '<nav class="sb-tools"', 1
        )[0]
        self.assertNotIn('<a ', board_columns)

    def test_board_exposes_complete_accessible_interaction_scenes(self):
        html = self.board_html()
        self.assertIn('id="sb-note-dialog"', html)
        self.assertIn('id="sb-note-form"', html)
        self.assertIn('id="sb-stats-dialog"', html)
        self.assertIn('id="sb-share-dialog"', html)
        self.assertIn('role="checkbox"', html)
        self.assertIn('draggable="true"', html)
        self.assertIn('data-add-checklist', html)
        self.assertIn('data-add-comment', html)
        self.assertIn('data-fullscreen', html)
        self.assertEqual(html.count('data-tool='), 9)
        self.assertEqual(html.count('<h2 class="sb-column__heading"'), 4)
        self.assertIn('Redesign the site to align with my vision', html)
        self.assertIn('Design new homepage', html)

    def test_storage_copy_remains_honest_for_both_feature_flag_states(self):
        browser_preview = self.board_html()
        self.assertIn('data-board-api="false"', browser_preview)
        self.assertIn('data-board-storage-scope="petec-preview"', browser_preview)
        self.assertIn('stay saved in this browser', browser_preview)

        app.config.update(
            PEERSLATE_DATABASE_UI_ENABLED=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY='slate-board-test-user',
        )
        database_preview = self.board_html()
        self.assertIn('data-board-api="true"', database_preview)
        self.assertRegex(database_preview, r'data-board-storage-scope="member-[a-f0-9]{20}"')
        self.assertIn('saved privately', database_preview)

        app.config.update(
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )
        signed_out_preview = self.board_html()
        self.assertIn('data-board-api="false"', signed_out_preview)
        self.assertIn('data-board-storage-scope="signed-out"', signed_out_preview)
        self.assertIn('stay saved in this browser', signed_out_preview)

    def test_dedicated_styles_include_mobile_and_accessibility_modes(self):
        css = Path('static/css/slate-board.css').read_text(encoding='utf-8')
        self.assertIn('@media (max-width: 719px)', css)
        self.assertIn('.sb-mobile-add', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('@media (forced-colors: active)', css)

        javascript = Path('static/js/slate-board.js').read_text(encoding='utf-8')
        self.assertIn('function cancelDrag()', javascript)
        self.assertIn('var pendingCreates = {};', javascript)
        self.assertIn("event.key === 'Enter'", javascript)


if __name__ == '__main__':
    unittest.main()
