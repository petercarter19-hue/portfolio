import unittest
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from app import app


QUIET_PREVIEW_DIRECTIVE = (
    b'<meta name="robots" '
    b'content="noindex, nofollow, noarchive, noimageindex">'
)


class SearchVisibilityQuietPreviewTests(unittest.TestCase):
    def setUp(self):
        self.original_testing = app.config.get("TESTING")
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(TESTING=self.original_testing)

    def test_direct_link_public_showcase_routes_remain_accessible(self):
        for path in (
            "/",
            "/experience",
            "/petec/my-story",
            "/petec/resume",
            "/interview-studio",
        ):
            with self.subTest(path=path):
                response = self.client.get(
                    path,
                    base_url="https://peerslate.com",
                )
                self.assertEqual(response.status_code, 200)

    def test_public_showcase_routes_are_noindex_during_quiet_preview(self):
        for path in (
            "/",
            "/experience",
            "/petec/my-story",
            "/petec/resume",
            "/interview-studio",
            "/peerslate",
        ):
            with self.subTest(path=path):
                response = self.client.get(
                    path,
                    base_url="https://peerslate.com",
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(QUIET_PREVIEW_DIRECTIVE, response.data)

    def test_every_route_still_advertised_by_the_sitemap_is_noindex(self):
        sitemap_response = self.client.get(
            "/sitemap.xml",
            base_url="https://peerslate.com",
        )
        self.assertEqual(sitemap_response.status_code, 200)
        root = ET.fromstring(sitemap_response.get_data(as_text=True))
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = root.findall("sitemap:url/sitemap:loc", namespace)
        self.assertTrue(locations)

        for location in locations:
            path = urlsplit(location.text).path
            with self.subTest(path=path):
                response = self.client.get(
                    path,
                    base_url="https://peerslate.com",
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(QUIET_PREVIEW_DIRECTIVE, response.data)

    def test_crawlers_can_read_the_noindex_directive(self):
        body = self.client.get(
            "/robots.txt",
            base_url="https://peerslate.com",
        ).get_data(as_text=True)

        self.assertIn("User-agent: *", body)
        self.assertIn("Allow: /", body)
        for protected_path in (
            "Disallow: /app",
            "Disallow: /api/",
            "Disallow: /owner",
            # PS-COMMUNITY-AUTH-WALL-001: the members-only Community
            # namespace stays out of crawl budget in every flag state.
            "Disallow: /the-slate",
        ):
            with self.subTest(protected_path=protected_path):
                self.assertIn(protected_path, body)

    def test_sitemap_never_advertises_the_members_only_community(self):
        # PS-COMMUNITY-AUTH-WALL-001: no protected Community route belongs in
        # the public sitemap, whichever way the flag points.
        original_flag = app.config.get("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED")
        try:
            for flag in (True, False):
                app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = flag
                response = self.client.get(
                    "/sitemap.xml",
                    base_url="https://peerslate.com",
                )
                self.assertEqual(response.status_code, 200)
                root = ET.fromstring(response.get_data(as_text=True))
                namespace = {
                    "sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"
                }
                locations = root.findall("sitemap:url/sitemap:loc", namespace)
                self.assertTrue(locations)
                for location in locations:
                    path = urlsplit(location.text).path
                    with self.subTest(flag=flag, path=path):
                        self.assertFalse(path.startswith("/the-slate"))
        finally:
            app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = original_flag


if __name__ == "__main__":
    unittest.main()
