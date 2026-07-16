"""Canonical Community Feed tests.

Community has one page with exactly two modes: member Feed and News Feed.
Old preview paths remain redirects only so existing bookmarks keep working.
"""

import os
import unittest

from app import app


class CommunityRouteTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_canonical_community_page_is_public(self):
        response = self.client.get('/the-slate', base_url='https://peerslate.com')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Community Feed', response.get_data(as_text=True))

    def test_retired_preview_paths_redirect_in_one_hop(self):
        for path, destination in (
            ('/feed-living-stream', '/the-slate'),
            ('/feed-living-stream/states', '/the-slate'),
            ('/_internal/feed-living-stream', '/the-slate'),
            ('/_internal/feed-living-stream/states', '/the-slate'),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith(destination))

    def test_voice_deep_link_is_preserved_when_retiring_old_address(self):
        response = self.client.get('/feed-living-stream?state=voice')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/the-slate?state=voice'))


class CommunityContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.html = cls.client.get('/the-slate').get_data(as_text=True)

    def test_exactly_two_community_modes_are_visible(self):
        self.assertIn('data-tab="feed">Feed</button>', self.html)
        self.assertIn('data-tab="news">News Feed</button>', self.html)
        self.assertEqual(self.html.count('data-tab="'), 2)

    def test_removed_community_concepts_are_not_rendered(self):
        for retired in ('Feed Preview', 'People &amp; Interests', 'My Slate', 'Daily Slate'):
            self.assertNotIn(retired, self.html)

    def test_private_note_is_the_only_right_rail_module(self):
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'static', 'js', 'feed-living-stream.js'
        )
        with open(script_path, encoding='utf-8') as script_file:
            script = script_file.read()
        self.assertIn('Journal Note', script)
        self.assertIn('Only you', script)
        for banned in ('Catch Up', 'Weekend Challenge', 'Recommended for You'):
            self.assertNotIn(banned, self.html + script)

    def test_private_note_moves_below_the_feed_on_narrow_viewports(self):
        css_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'static', 'css', 'feed-living-stream.css'
        )
        with open(css_path, encoding='utf-8') as css_file:
            css = css_file.read()
        self.assertIn(
            '.context-rail{display:block;position:static;margin-top:18px}',
            css,
        )
        self.assertNotIn('.context-rail{display:none}', css)

    def test_accessibility_and_shared_chrome_remain_intact(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('Skip to main content', self.html)
        self.assertIn('class="global-header"', self.html)
        self.assertNotIn('class="profile-tabs', self.html)

    def test_respond_vocabulary_is_kept(self):
        with open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'js', 'feed-living-stream.js'),
            encoding='utf-8',
        ) as script_file:
            script = script_file.read()
        for label in ('Celebrate', 'Support', 'I relate', 'Ask', 'Offer help'):
            self.assertIn(label, script)


class CommunityDiscoverabilityTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_homepage_uses_canonical_community_links(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('/the-slate?state=voice', html)
        self.assertNotIn('/feed-living-stream', html)

    def test_search_index_has_only_current_community_destinations(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('Community · Feed', html)
        self.assertIn('Community · News Feed', html)
        for retired in ('Feed Preview', 'People &amp; Interests', 'Community · My Slate', 'Community · Daily Slate'):
            self.assertNotIn(retired, html)


class CommunityAssetTests(unittest.TestCase):
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_static_files_exist(self):
        for rel in ('static/css/feed-living-stream.css', 'static/js/feed-living-stream.js'):
            self.assertTrue(os.path.isfile(os.path.join(self.ROOT, rel)), rel)


if __name__ == '__main__':
    unittest.main()
