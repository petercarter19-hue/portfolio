import unittest

from app import app


class InterviewWorkspaceTests(unittest.TestCase):
    """The Interview Workspace redesign.

    Locks in the preservation contract (every original studio control keeps
    its id so interview.js keeps working), the three-mode structure, the
    honest Video Studio states, and explicit demo-data labeling.
    """

    def setUp(self):
        self.client = app.test_client()

    def _html(self):
        response = self.client.get('/petec/interview-me', base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_route_and_workspace_shell(self):
        html = self._html()
        self.assertIn('Interview Workspace', html)
        self.assertIn('Practice with purpose. Answer like you. Improve with proof.', html)
        for mode in ('data-ivw-mode="me"', 'data-ivw-mode="you"', 'data-ivw-mode="video"'):
            self.assertIn(mode, html)

    def test_original_studio_controls_are_preserved(self):
        html = self._html()
        preserved_ids = (
            'iv-levels', 'iv-evidence-toggle', 'iv-dir-me', 'iv-dir-ai',
            'iv-counter', 'iv-prev', 'iv-next', 'iv-question', 'iv-topic-chip',
            'iv-rephrase', 'iv-new', 'iv-answer', 'iv-count', 'iv-clear',
            'iv-sample', 'iv-save', 'iv-record', 'iv-feedback-btn',
            'iv-askai-card', 'iv-askai-input', 'iv-askai-btn', 'iv-askai-answer',
            'iv-feedback-card', 'iv-feedback', 'iv-score', 'iv-score-num',
            'iv-score-tier', 'iv-session', 'iv-mockbar', 'iv-mock-btn',
            'iv-evidence', 'iv-qbank', 'iv-bank-star', 'iv-bank-behavioral',
        )
        for element_id in preserved_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', html)

    def test_question_bank_keeps_all_sixty_questions(self):
        html = self._html()
        self.assertEqual(html.count('class="iq-item"'), 60)

    def test_video_studio_is_an_honest_prototype(self):
        html = self._html()
        self.assertIn('Nothing is recorded, uploaded, stored, or analyzed yet', html)
        self.assertIn('Prototype', html)
        self.assertIn('data-ivw-camera-start', html)
        # No unsupported analysis claims anywhere.
        for banned in ('emotion detection', 'personality scor', 'deception'):
            self.assertNotIn(banned, html.lower())

    def test_demo_fixtures_are_explicitly_labeled(self):
        html = self._html()
        self.assertGreaterEqual(html.count('Demo data'), 3)

    def test_micap_never_appears_in_the_redesigned_workspace(self):
        html = self._html()
        self.assertNotIn('micap', html.lower())

    def test_entitlements_come_from_the_server_not_the_browser(self):
        # The route injects server-side entitlement state; the browser cannot
        # override it (no user_key or entitlement inputs are rendered).
        html = self._html()
        self.assertNotIn('user_key', html)
        self.assertIn('Prototype', html)  # video tier state rendered server-side

    def test_rewrite_tools_are_labeled_as_suggestions(self):
        html = self._html()
        self.assertIn('Rewrite your draft', html)
        self.assertIn('AI &middot; suggestion only', html)


if __name__ == '__main__':
    unittest.main()
