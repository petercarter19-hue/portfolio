"""The authenticated Community replaces every pre-pilot Community surface.

Pete, 2026-08-03: "this is the new community feed. It replaces the old one.
Anyplace there is a community link, it goes to the new page. The old one
should be archived."

PS-COMMUNITY-AUTH-WALL-001 finishes the archiving and retires the public
demo: the pre-pilot shells never render again in ANY flag state. Their
historical human addresses forward to the one real Community, which now
requires sign-in — flag off is a neutral 404, not an older feed.
"""

import json
import re
import unittest
from uuid import uuid4

from app import app


RETIRED_ROUTES = (
    "/the-slate/my-slate",
    "/the-slate/daily",
    "/the-slate/pulse",
    "/the-slate/break",
)
ALREADY_REDIRECTING = (
    "/the-slate/paths",
    "/the-slate/progress",
    "/the-slate/saved",
    "/the-slate/people-interests",
)
RETIRED_SEARCH_TITLES = (
    '"title": "Living Stream"',
    '"title": "My Slate"',
    '"title": "Daily Slate"',
    '"title": "Slate Paths"',
    '"title": "Slate Pulse"',
    '"title": "The Break"',
)


def _search_index_entries(body):
    """Parse the rendered #nav-search-data destination index."""
    match = re.search(
        r'<script id="nav-search-data" type="application/json">\s*(\[.*?\])\s*</script>',
        body,
        re.DOTALL,
    )
    assert match, "the header search index block is missing"
    return json.loads(match.group(1))


class ConfigSnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(TESTING=True, PEERSLATE_DEV_USER_KEY=None)
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)


class RetiredRoutesWithFlagOffTests(ConfigSnapshotTestCase):
    """Flag off no longer resurrects the pre-pilot Community.

    The old premise ("the pre-pilot Community must keep working until the
    pilot is on") is dead: the retired routes redirect and the Community
    landing is a neutral 404 with the flag OFF too.
    """

    def setUp(self):
        super().setUp()
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False

    def test_every_retired_route_redirects_even_with_the_flag_off(self):
        for route in RETIRED_ROUTES + ALREADY_REDIRECTING:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 302)

    def test_the_slate_is_a_neutral_404_that_renders_no_community_shell(self):
        response = self.client.get("/the-slate")
        self.assertEqual(response.status_code, 404)
        body = response.get_data(as_text=True)
        # Neither the new member shell nor the old tabbed shell renders.
        self.assertNotIn("cv1-shell", body)
        self.assertNotIn("The Break", body)

    def test_search_never_offers_the_retired_views_with_the_flag_off(self):
        body = self.client.get("/").get_data(as_text=True)
        for retired in ("slate_feed_break", "/the-slate/break", "/the-slate/pulse"):
            with self.subTest(entry=retired):
                self.assertNotIn(retired, body)
        for title in RETIRED_SEARCH_TITLES:
            with self.subTest(entry=title):
                self.assertNotIn(title, body)


class NewCommunityReplacesOldTests(ConfigSnapshotTestCase):
    def setUp(self):
        super().setUp()
        app.config.update(
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_OWNER_USER_KEYS=str(uuid4()),
            PEERSLATE_OWNER_EMAILS="",
            PEERSLATE_COMMUNITY_SIGNING_KEY="community-test-signing-key",
        )

    def test_every_retired_route_redirects_to_the_new_community(self):
        for route in RETIRED_ROUTES:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response.headers["Location"].endswith("/the-slate"),
                    f"{route} should land on the new Community feed",
                )

    def test_the_previously_redirecting_routes_are_unchanged(self):
        for route in ALREADY_REDIRECTING:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 302)

    def test_search_no_longer_offers_the_retired_views(self):
        # Offering a retired page and then bouncing the visitor is worse than
        # not offering it.
        body = self.client.get("/").get_data(as_text=True)
        for retired in ("slate_feed_break", "/the-slate/break", "/the-slate/pulse"):
            with self.subTest(entry=retired):
                self.assertNotIn(retired, body)
        for title in RETIRED_SEARCH_TITLES:
            with self.subTest(entry=title):
                self.assertNotIn(title, body)

    def test_search_offers_exactly_one_community_entry(self):
        entries = _search_index_entries(self.client.get("/").get_data(as_text=True))
        community = [entry for entry in entries if entry["title"] == "Community"]
        self.assertEqual(len(community), 1)
        self.assertEqual(community[0]["href"], "/the-slate")

    def test_the_community_nav_link_reaches_the_one_real_feed(self):
        # Every Community link in the shell points at this one route, so this
        # is what "anyplace there is a community link" resolves to. Signed
        # out it goes through sign-in and back to this exact page; a member
        # gets the real feed.
        signed_out = self.client.get("/the-slate")
        self.assertEqual(signed_out.status_code, 302)
        self.assertEqual(
            signed_out.headers["Location"], "/auth/sign-in?return_to=/the-slate"
        )

        app.config["PEERSLATE_DEV_USER_KEY"] = str(uuid4())
        member = self.client.get("/the-slate")
        self.assertEqual(member.status_code, 200)
        self.assertIn(b"community-v1.css", member.data)
        self.assertIn(b"cv1-shell", member.data)


class SearchIndexTemplateTests(unittest.TestCase):
    """Static contract on base.html's destination index, both branches."""

    @classmethod
    def setUpClass(cls):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        template = (root / "templates" / "base.html").read_text(encoding="utf-8")
        start = template.index('<script id="nav-search-data"')
        cls.index_block = template[start : template.index("</script>", start)]

    def test_each_branch_has_exactly_one_community_entry_reaching_the_slate(self):
        # One owner-branch entry and one public-branch entry.
        self.assertEqual(self.index_block.count('"title": "Community"'), 2)
        self.assertEqual(
            self.index_block.count("url_for('the_slate')"), 2
        )

    def test_no_branch_offers_a_living_stream_or_legacy_slate_entry(self):
        for title in RETIRED_SEARCH_TITLES:
            with self.subTest(entry=title):
                self.assertNotIn(title, self.index_block)
        self.assertNotIn("feed_living_stream", self.index_block)
        self.assertNotIn("feed-living-stream", self.index_block)


if __name__ == "__main__":
    unittest.main()
