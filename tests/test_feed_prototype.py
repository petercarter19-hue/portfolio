"""PS-FEED-001 — Living Stream Feed prototype route tests.

The prototype is a public design preview (fixture data only). These tests
pin: the public routes and legacy redirect, the visible preview-banner
copy that keeps visitors from mistaking sample data for real
functionality, the copy-deck language that defines the alpha Feed, the
absence of banned filler concepts, the discoverability links added to
real navigation, and the static assets the page depends on.
"""

import os
import unittest

from app import app


class FeedPrototypeRouteTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_prototype_route_is_public(self):
        response = self.client.get(
            '/feed-living-stream', base_url='https://peerslate.com')
        self.assertEqual(response.status_code, 200)

    def test_states_route_is_public(self):
        response = self.client.get(
            '/feed-living-stream/states', base_url='https://peerslate.com')
        self.assertEqual(response.status_code, 200)

    def test_legacy_internal_path_redirects(self):
        response = self.client.get('/_internal/feed-living-stream')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/feed-living-stream'))

    def test_legacy_internal_states_path_redirects(self):
        response = self.client.get('/_internal/feed-living-stream/states')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/feed-living-stream/states'))

    def test_states_map_route(self):
        response = self.client.get('/feed-living-stream/states')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('?state=voice', html)
        self.assertIn('?state=publish', html)
        self.assertIn('?state=error', html)


class FeedPrototypeContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.html = app.test_client().get('/feed-living-stream').get_data(as_text=True)

    def test_alpha_tabs_only(self):
        self.assertIn('For You', self.html)
        self.assertIn('Following', self.html)

    def test_copy_deck_language(self):
        self.assertIn('Feed', self.html)
        self.assertIn('What people are building, learning, and living.', self.html)

    def test_preview_banner_present(self):
        self.assertIn('Design preview', self.html)
        self.assertIn('sample data', self.html)
        self.assertIn('saved to a database', self.html)

    def test_no_banned_filler_language(self):
        # Scoped to the Feed experience itself (#feed-app onward). The
        # global chrome from base.html is shared by every page and contains
        # a pre-existing search keyword ("trending" on the Pulse entry)
        # that is not part of this Feed design.
        feed_app = self.html[self.html.index('id="feed-app"'):]
        feed_app = feed_app[:feed_app.index('</script>')]
        lowered = feed_app.lower()
        for banned in ('trending', 'top creators', 'influencer',
                       'thought leaders', 'boost your brand'):
            self.assertNotIn(banned, lowered)

    def test_accessibility_landmarks(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('Skip to main content', self.html)

    def test_real_global_header_is_present(self):
        """Pete's chrome rule (2026-07-16): the site's top navigation bar is
        identical on every page — the preview must render the real global
        header, not its own imitation of one."""
        self.assertIn('class="global-header"', self.html)
        self.assertIn('platform-nav', self.html)
        self.assertIn("Pete's Slate", self.html)
        self.assertIn('Interview Studio', self.html)
        self.assertIn('About PeerSlate', self.html)


class FeedPrototypeDiscoverabilityTests(unittest.TestCase):
    """The prototype must be reachable by browsing the real site, not only
    by a direct link — per Pete's explicit request on 2026-07-16."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_linked_from_header_search_index(self):
        home_html = self.client.get('/').get_data(as_text=True)
        self.assertIn('/feed-living-stream', home_html)
        self.assertIn('Feed Preview', home_html)

    def test_linked_from_community_feed_hub(self):
        community_html = self.client.get('/the-slate').get_data(as_text=True)
        self.assertIn('/feed-living-stream', community_html)
        self.assertIn('Feed Preview', community_html)


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
