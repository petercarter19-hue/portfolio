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
        self.assertIn('?state=preview', html)
        self.assertIn('?state=error', html)


class FeedPrototypeContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.html = app.test_client().get('/feed-living-stream').get_data(as_text=True)

    def test_community_switcher_tabs(self):
        # 2026-07-17 (Pete, round 2): the Feed and The Break are one
        # ecosystem — a prominent two-tab switcher flips between them, and
        # the shared community sidebar appears on both. People & Interests
        # left the switcher; For You / Following never returns.
        self.assertIn('feed-switch', self.html)
        self.assertIn('The Break', self.html)
        self.assertIn('aria-label="Community sections"', self.html)
        self.assertNotIn('People &amp; Interests', self.html)
        self.assertNotIn('Following', self.html)
        self.assertNotIn('For You', self.html)

    def test_copy_deck_language(self):
        self.assertIn('Feed', self.html)
        self.assertIn('What people are building, learning, and living.', self.html)

    def test_sample_data_note_present(self):
        # 2026-07-17 (Pete): the loud "Design preview" badge is gone, but the
        # truthfulness rule stands — one quiet line still says the page is
        # sample data and saves nothing.
        self.assertNotIn('Design preview', self.html)
        self.assertIn('Sample data — nothing on this page is saved or shared.', self.html)

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
        # The old For You / Following tablist is now a labeled nav of links.
        self.assertIn('aria-label="Community views"', self.html)
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
        # v1.2: About left the header; Why PeerSlate lives in the footer.
        self.assertNotIn('>About PeerSlate</a>', self.html)
        self.assertIn('Why PeerSlate', self.html)


class FeedPrototypeDiscoverabilityTests(unittest.TestCase):
    """The retained comparison route is no longer a public navigation item.

    PS-PUBLIC-NAV-001 removes preview and fixture destinations from the
    authoritative public shell while leaving the direct rollback route intact.
    """

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_header_search_does_not_publish_the_preview(self):
        home_html = self.client.get('/').get_data(as_text=True)
        search_data = home_html.split(
            '<script id="nav-search-data"', 1)[1].split('</script>', 1)[0]
        self.assertNotIn('/feed-living-stream', search_data)
        self.assertNotIn('Feed Preview', search_data)

    def test_community_feed_does_not_publish_the_preview(self):
        community_html = self.client.get('/the-slate').get_data(as_text=True)
        search_data = community_html.split(
            '<script id="nav-search-data"', 1)[1].split('</script>', 1)[0]
        self.assertNotIn('/feed-living-stream', search_data)
        self.assertNotIn('Feed Preview', search_data)


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
