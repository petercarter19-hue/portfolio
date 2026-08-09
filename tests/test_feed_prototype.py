"""PS-FEED-001 — Living Stream Feed prototype retirement tests.

The prototype was a public design preview (fixture data only). Its working
anonymous demo is retired by PS-COMMUNITY-AUTH-WALL-001: the widely shared
human address forwards to the real Community (which requires sign-in), the
preview/state pages are gone in every flag state, and no navigation surface
publishes the preview. The templates and static assets stay on disk,
unrouted, as the rollback/history record.
"""

import os
import unittest

from app import app


class FeedPrototypeRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    def test_prototype_address_forwards_to_the_real_community(self):
        # The shared human address keeps working, but it lands on the one
        # real Community — in both flag states.
        for flag in (True, False):
            with self.subTest(flag=flag):
                app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = flag
                response = self.client.get(
                    "/feed-living-stream", base_url="https://peerslate.com"
                )
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith("/the-slate"))

    def test_states_and_internal_preview_pages_are_gone(self):
        for flag in (True, False):
            app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = flag
            for path in (
                "/feed-living-stream/states",
                "/_internal/feed-living-stream",
                "/_internal/feed-living-stream/states",
            ):
                with self.subTest(flag=flag, path=path):
                    self.assertEqual(self.client.get(path).status_code, 404)


class FeedPrototypeRetirementTests(unittest.TestCase):
    """The redirect serves none of the old preview experience."""

    @classmethod
    def setUpClass(cls):
        cls.previous_config = dict(app.config)
        app.config.update(TESTING=True)
        cls.response = app.test_client().get("/feed-living-stream")
        cls.html = cls.response.get_data(as_text=True)

    @classmethod
    def tearDownClass(cls):
        app.config.clear()
        app.config.update(cls.previous_config)

    def test_no_preview_markup_is_served_from_the_retired_address(self):
        self.assertEqual(self.response.status_code, 302)
        for retired in (
            'id="feed-app"',
            "feed-switch",
            'aria-label="Community views"',
            "Sample data — nothing on this page is saved or shared.",
            "What people are building, learning, and living.",
            "feed-living-stream.js",
        ):
            with self.subTest(marker=retired):
                self.assertNotIn(retired, self.html)

    def test_archived_templates_remain_on_disk_unrouted(self):
        # The rollback/history record stays; nothing renders it. (app.py's
        # retired-route handlers redirect or 404 without touching these.)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in (
            "templates/feed_living_stream.html",
            "templates/feed_living_stream_states.html",
        ):
            self.assertTrue(os.path.isfile(os.path.join(root, rel)), rel)


class FeedPrototypeDiscoverabilityTests(unittest.TestCase):
    """No navigation surface publishes the retired preview.

    PS-PUBLIC-NAV-001 removed preview and fixture destinations from the
    authoritative public shell; PS-COMMUNITY-AUTH-WALL-001 retired the
    preview routes themselves.
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

    def test_community_response_does_not_publish_the_preview(self):
        # Whatever /the-slate answers (sign-in redirect, neutral 404, or a
        # member render), the shared chrome never advertises the preview.
        response = self.client.get('/the-slate')
        html = response.get_data(as_text=True)
        self.assertNotIn('/feed-living-stream', html)
        self.assertNotIn('Feed Preview', html)


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
