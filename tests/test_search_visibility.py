import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
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
            # PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001: unconditional
            # in both flag states (architecture 04 section 1).
            "Disallow: /interview-studio",
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

    def test_sitemap_never_advertises_interview_studio_in_either_flag_state(self):
        # PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001: removed from the
        # public sitemap unconditionally (architecture 04 section 1) — this
        # is correct while the page is still public and once it is gated.
        original_flag = app.config.get("PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED")
        try:
            for flag in (True, False):
                app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = flag
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
                        self.assertFalse(path.startswith("/interview-studio"))
        finally:
            app.config["PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED"] = original_flag


class ShellSearchScopeTests(unittest.TestCase):
    """The shared shell keeps one navigation-only search implementation.

    Public-profile detail stays on public pages. Protected pages add only the
    real My PeerSlate and Settings destinations; no owner content, capture
    records, or AI fallback enters the index.
    """

    def setUp(self):
        self.client = app.test_client()

    def index_records(self, path="/"):
        response = self.client.get(path, base_url="http://localhost")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        block = body.split('<script id="nav-search-data" type="application/json">', 1)[1]
        return json.loads(block.split("</script>", 1)[0])

    def test_the_destination_index_is_unchanged_and_still_destination_only(self):
        records = self.index_records()
        self.assertTrue(records)
        for record in records:
            with self.subTest(title=record["title"]):
                self.assertEqual(
                    sorted(record), ["href", "keys", "sub", "title"]
                )
                self.assertTrue(record["href"].startswith(("/", "http")))
        # No content search: every entry is a route or a static file, and
        # none of them is a member-authored record.
        self.assertFalse(
            [r for r in records if r["href"].startswith("/api/")]
        )

    def test_public_search_does_not_expose_protected_account_destinations(self):
        for path in ("/", "/interview-studio"):
            with self.subTest(path=path):
                titles = [r["title"] for r in self.index_records(path)]
                for absent in ("Settings", "My PeerSlate", "Capture",
                               "Sign out", "More", "Account"):
                    self.assertNotIn(absent, titles)

    def test_protected_search_has_real_account_destinations_but_no_content(self):
        originals = {
            key: app.config.get(key)
            for key in ("PEERSLATE_ALLOW_DEV_IDENTITY", "PEERSLATE_DEV_USER_KEY")
        }
        app.config.update(
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="shell-search-member",
        )
        try:
            records = self.index_records("/app")
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

        titles = {record["title"] for record in records}
        self.assertIn("My PeerSlate", titles)
        self.assertIn("Settings", titles)
        for absent in ("Capture", "Sign out", "More", "Account", "Ask Pete"):
            self.assertNotIn(absent, titles)
        self.assertFalse([r for r in records if r["href"].startswith("/api/")])

    def test_newly_linked_protected_routes_stay_out_of_crawl_scope(self):
        """The More sheet links /app/settings for a signed-in member. That
        namespace must remain uncrawlable and unadvertised."""
        robots = self.client.get(
            "/robots.txt", base_url="https://peerslate.com"
        ).get_data(as_text=True)
        self.assertIn("Disallow: /app", robots)

        sitemap = self.client.get(
            "/sitemap.xml", base_url="https://peerslate.com"
        )
        root = ET.fromstring(sitemap.get_data(as_text=True))
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for location in root.findall("sitemap:url/sitemap:loc", namespace):
            path = urlsplit(location.text).path
            with self.subTest(path=path):
                self.assertFalse(path.startswith("/app"))

    def test_there_is_exactly_one_search_field_in_the_shell(self):
        """The released shell carried two: a header field hidden below
        73.75rem, and a second one inside the phone sheet. The header field is
        now present at every width, so keeping the sheet's copy meant two
        visible inputs — and two controls with the same accessible name —
        whenever the sheet was open. Rendered markup, not stylesheet text:
        one input, one results panel, one accessible name."""
        for path in ("/", "/interview-studio", "/petec/resume"):
            with self.subTest(path=path):
                body = self.client.get(
                    path, base_url="http://localhost"
                ).get_data(as_text=True)
                self.assertEqual(body.count('class="nav-search__input"'), 1)
                self.assertEqual(body.count('class="nav-search__results"'), 1)
                self.assertEqual(body.count('aria-label="Search PeerSlate"'), 1)
                self.assertNotIn('id="nav-search-input-mobile"', body)
                self.assertIn('id="nav-search-input"', body)

    def test_search_authorization_and_behaviour_are_untouched(self):
        source = Path("static/js/public-site-search.js").read_text(encoding="utf-8")
        self.assertIn("No matching destination", source)
        self.assertNotIn("Ask Pete", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("credentials", source)
        # The index is read from the server-rendered block and nowhere else.
        self.assertIn("document.getElementById('nav-search-data')", source)


if __name__ == "__main__":
    unittest.main()
