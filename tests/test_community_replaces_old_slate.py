"""The new Community feed replaces the pre-pilot Community.

Pete, 2026-08-03: "this is the new community feed. It replaces the old one.
Anyplace there is a community link, it goes to the new page. The old one
should be archived."

The archiving is flag-aware on purpose. While the pilot flag is off, the
pre-pilot Community is still the live site, so these tests assert both
directions: nothing changes today, and everything redirects once the flag
turns on.
"""

import unittest

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


class OldCommunityStillLiveWhileFlagOffTests(unittest.TestCase):
    """The pre-pilot Community must keep working until the pilot is on."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False
        self.client = app.test_client()

    def test_every_retired_route_still_serves_its_page(self):
        for route in RETIRED_ROUTES:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_the_slate_still_serves_the_old_community(self):
        response = self.client.get("/the-slate")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"cv1-shell", response.data)

    def test_search_still_offers_the_old_community_views(self):
        # /the-slate renders the public search branch, which lists The Break.
        body = self.client.get("/the-slate").get_data(as_text=True)
        self.assertIn("The Break", body)


class NewCommunityReplacesOldTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = True
        self.client = app.test_client()

    def tearDown(self):
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False

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
        body = self.client.get("/the-slate").get_data(as_text=True)
        for retired in ("The Break", "slate_feed_break", "/the-slate/break"):
            with self.subTest(entry=retired):
                self.assertNotIn(retired, body)

    def test_search_still_offers_community_itself(self):
        body = self.client.get("/the-slate").get_data(as_text=True)
        self.assertIn("Community Feed", body)

    def test_the_community_nav_link_reaches_the_new_feed(self):
        # Every Community link in the shell points at this one route, so this
        # is what "anyplace there is a community link" resolves to.
        response = self.client.get("/the-slate")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"community-v1.css", response.data)


if __name__ == "__main__":
    unittest.main()
