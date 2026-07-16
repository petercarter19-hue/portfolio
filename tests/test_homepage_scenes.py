"""PS-HOME-STORY-001 — three-scene homepage tests.

Pins the acceptance criteria that matter most: the shared header survives,
every CTA resolves through a real route, the scene content comes from the
approved live sources, the banned mockup content never appears, and the
old homepage remains reachable at /experience for rollback.
"""

import unittest

from app import app


class HomepageSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.html = cls.client.get('/').get_data(as_text=True)

    # ---- shell ----

    def test_homepage_renders(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_single_h1(self):
        self.assertEqual(self.html.count('<h1'), 1)

    def test_shared_global_header_untouched(self):
        for expected in ('class="global-header"', "Pete's Slate", 'Community',
                         'Interview Studio', 'Why PeerSlate', 'Ask AI',
                         'Sign In'):
            self.assertIn(expected, self.html)

    def test_no_mockup_only_navigation(self):
        for banned in ('How It Works', 'Explore a Slate', 'For Teams',
                       'Pricing', 'Create My Slate'):
            self.assertNotIn(banned, self.html)

    def test_old_homepage_still_reachable_for_rollback(self):
        response = self.client.get('/experience')
        self.assertEqual(response.status_code, 200)
        self.assertIn('cinematic-home-page',
                      response.get_data(as_text=True))

    # ---- scene content ----

    def test_scene_headlines_present(self):
        self.assertIn('Say what happened.', self.html)
        self.assertIn('grounded in the real thing.', self.html)
        self.assertIn('Go beyond', self.html)
        self.assertIn('Enter once. Link everywhere. Publish deliberately.',
                      self.html)

    def test_four_act_labels_match_live_story(self):
        for label in ('This is me now', 'How I became this person',
                      'The life around the work', 'Still becoming'):
            self.assertIn(label, self.html)

    def test_live_polaroid_captions_present(self):
        self.assertIn('100 miles. 10 days. One goal.', self.html)
        self.assertIn('Places that changed me.', self.html)
        self.assertIn('Always get outside.', self.html)

    def test_banned_mockup_captions_absent(self):
        for banned in ('First marathon — 2018', 'First marathon - 2018',
                       'Bali — reset &amp; refocus', 'Bali — reset & refocus',
                       'Hawaii — perspective'):
            self.assertNotIn(banned, self.html)

    def test_future_card_uses_approved_content(self):
        self.assertIn('Systems Engineering Ph.D.', self.html)
        self.assertIn('University of South Alabama', self.html)
        self.assertIn('January 2027', self.html)
        self.assertIn('Cameo Systems Modeler', self.html)
        self.assertIn('Mentoring', self.html)

    def test_no_browser_local_board_notes(self):
        lowered = self.html.lower()
        for banned in ('grocery', 'second home', 'guitar'):
            self.assertNotIn(banned, lowered)

    def test_resume_metrics_come_from_live_source(self):
        for value in ('30+', '9 / $19.2M', '$36M+', '70%', '35%'):
            self.assertIn(value, self.html)
        self.assertIn('The Career Constellation', self.html)
        self.assertIn('Northrop Grumman', self.html)

    def test_no_fabricated_trusted_by_logos(self):
        for banned in ('Google', 'Microsoft', 'NVIDIA', 'Deloitte',
                       'amazon'):
            self.assertNotIn(banned, self.html)

    # ---- links ----

    def test_ctas_resolve_to_real_routes(self):
        for href in ('/petec/my-story', '/petec/skills', '/petec/resume',
                     '/petec/slate-board', '/the-slate?state=voice',
                     '/petec/slate-board#daily-check-in',
                     '/petec/projects', '/interview-studio'):
            self.assertIn('href="%s' % href, self.html)
            target = href.split('#')[0].split('?')[0]
            status = self.client.get(target).status_code
            self.assertIn(status, (200, 302), target)

    def test_read_the_chapters_anchor_exists_on_story_page(self):
        self.assertIn('href="/petec/my-story#act-becoming"', self.html)
        story_html = self.client.get('/petec/my-story').get_data(as_text=True)
        self.assertIn('id="act-becoming"', story_html)

    # ---- semantics ----

    def test_polaroids_are_semantic_figures(self):
        self.assertEqual(self.html.count('hv-polaroid hv-polaroid--'), 3)
        self.assertIn('<figcaption', self.html)
        self.assertIn('Pete running a 10K race wearing bib number 4465',
                      self.html)

    def test_act_index_is_an_ordered_list(self):
        self.assertIn('<ol class="hv-acts"', self.html)


if __name__ == '__main__':
    unittest.main()
