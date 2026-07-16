"""PS-FEED-001 — Living Stream Feed prototype route tests.

The prototype is an internal preview (fixture data only). These tests pin:
- the internal-preview gate (local always, env flag for deployed review),
- the copy-deck language that defines the alpha Feed,
- the absence of banned filler concepts,
- the static assets the page depends on.
"""

import os
import unittest
from unittest import mock

from app import app


class FeedPrototypeRouteTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_local_request_renders_prototype(self):
        response = self.client.get('/_internal/feed-living-stream')
        self.assertEqual(response.status_code, 200)

    def test_non_local_request_is_hidden_without_flag(self):
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop('ENABLE_FEED_PROTOTYPE', None)
            os.environ.pop('ENABLE_DESIGN_SYSTEM_PREVIEW', None)
            response = self.client.get(
                '/_internal/feed-living-stream',
                base_url='https://peerslate.com',
            )
        self.assertEqual(response.status_code, 404)

    def test_non_local_request_allowed_with_flag(self):
        with mock.patch.dict(os.environ, {'ENABLE_FEED_PROTOTYPE': '1'}):
            response = self.client.get(
                '/_internal/feed-living-stream',
                base_url='https://peerslate.com',
            )
        self.assertEqual(response.status_code, 200)

    def test_states_map_route(self):
        response = self.client.get('/_internal/feed-living-stream/states')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('?state=voice', html)
        self.assertIn('?state=publish', html)
        self.assertIn('?state=error', html)


class FeedPrototypeContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.html = app.test_client().get(
            '/_internal/feed-living-stream'
        ).get_data(as_text=True)

    def test_alpha_tabs_only(self):
        self.assertIn('For You', self.html)
        self.assertIn('Following', self.html)

    def test_copy_deck_language(self):
        self.assertIn('Feed', self.html)
        self.assertIn('What people are building, learning, and living.', self.html)

    def test_no_banned_filler_language(self):
        lowered = self.html.lower()
        for banned in ('trending', 'top creators', 'influencer',
                       'thought leaders', 'boost your brand'):
            self.assertNotIn(banned, lowered)

    def test_accessibility_landmarks(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('Skip to Feed', self.html)


class FeedPrototypeAssetTests(unittest.TestCase):
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_static_files_exist(self):
        for rel in (
            'static/css/feed-living-stream.css',
            'static/js/feed-living-stream.js',
        ):
            self.assertTrue(
                os.path.isfile(os.path.join(self.ROOT, rel)), rel)

    def test_fixture_media_exists(self):
        feed_dir = os.path.join(self.ROOT, 'static', 'images', 'feed')
        for name in (
            'work_whiteboard.jpg', 'surf_morning.jpg', 'keyboard_build.jpg',
            'coffee_notes.jpg', 'office_prototype.jpg', 'whiteboard_close.jpg',
            'dinner_served.jpg',
        ):
            self.assertTrue(
                os.path.isfile(os.path.join(feed_dir, name)), name)


if __name__ == '__main__':
    unittest.main()
