"""People & Interests living board (PS-FEAT-002) — retirement and service tests.

PS-COMMUNITY-AUTH-WALL-001 retired the board's public HTTP surface: the
people_interests_api blueprint is never registered (no flag state may
resurrect a public or fixture Community feed), and the board's page long ago
left /the-slate. The untouched in-process service
(services/people_interests_feed.py) keeps direct unit coverage below, and the
fixture contract tests are unchanged.
"""

import json
import os
import unittest
from unittest.mock import patch

from app import app
from services.people_interests_feed import (
    CONTENT_TYPES,
    POST_BODY_MAX,
    REACTION_KEYS,
    FeedNotFoundError,
    FeedValidationError,
    PeopleInterestsFeed,
)


class PeopleInterestsPageTests(unittest.TestCase):
    """The board retired as the /the-slate landing on 2026-07-21
    (PS-COMMUNITY-TABS-001); PS-COMMUNITY-AUTH-WALL-001 then retired the
    whole public shell. The one real Community renders only for a signed-in
    member and never shows the board."""

    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY="board-member-not-owner",
            PEERSLATE_OWNER_USER_KEYS="someone-else-entirely",
            PEERSLATE_OWNER_EMAILS="",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    def test_the_slate_landing_is_the_authenticated_community(self):
        response = self.client.get("/the-slate")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("cv1-shell", html)
        for retired in (
            "People &amp; Interests",
            "pi-board",
            "pi-initial-feed",
            'id="feed-app"',
            'id="feedColumn"',
            "What people are building, learning, and living.",
        ):
            with self.subTest(marker=retired):
                self.assertNotIn(retired, html)

    def test_old_board_address_forwards_to_the_slate(self):
        response = self.client.get("/the-slate/people-interests")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/the-slate"))

    def test_slate_board_remains_reachable_from_the_landing(self):
        # Pete's Slate navigation still never leaks into Community. Slate
        # Board remains discoverable through the public destination search.
        html = self.client.get("/the-slate").get_data(as_text=True)
        self.assertIn("Slate Board", html)
        self.assertIn('"href": "/petec/slate-board"', html)
        self.assertNotIn('class="profile-tabs', html)

    def test_page_keeps_global_header_without_the_retired_switcher(self):
        html = self.client.get("/the-slate").get_data(as_text=True)
        # Community keeps the global header; the old People & Interests /
        # Feed / The Break switcher strip is retired with the public shell.
        self.assertIn("platform-nav", html)
        self.assertNotIn("profile-tabs", html)
        self.assertNotIn("People &amp; Interests", html)
        self.assertNotIn("data-comm-tab", html)
        self.assertNotIn("News Feed", html)

    def test_legacy_subview_addresses_redirect_to_community(self):
        # PS-COMMUNITY-AUTH-WALL-001: the neighbours are retired too — every
        # legacy subview forwards to the one real Community.
        for path in (
            "/the-slate/break", "/the-slate/daily",
            "/the-slate/my-slate", "/the-slate/pulse",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url="http://localhost")
                self.assertEqual(response.status_code, 302)
                self.assertTrue(
                    response.headers["Location"].endswith("/the-slate")
                )

    def test_no_category_filter_row_above_the_feed(self):
        # The retired board mockup's All/People/Goals/... filter buttons
        # never return.
        html = self.client.get("/the-slate").get_data(as_text=True)
        self.assertNotIn("pi-filters", html)


class PeopleInterestsApiRetirementTests(unittest.TestCase):
    """PS-COMMUNITY-AUTH-WALL-001: the fixture-backed people_interests_api
    blueprint is never registered. Every board address is a neutral 404 in
    both flag states, and no request reaches the feed service."""

    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="test-user-1",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    @patch("people_interests_api.people_interests_feed.get_page")
    @patch("people_interests_api.people_interests_feed.get_post_detail")
    def test_every_board_api_address_is_404_in_both_flag_states(
        self, get_post_detail, get_page
    ):
        headers = {"X-PeerSlate-Request": "same-origin"}
        requests = (
            ("GET", "/api/feed/people-interests", {}),
            ("GET", "/api/feed/people-interests?limit=16", {}),
            ("GET", "/api/feed/posts/pi-maya-half", {}),
            (
                "POST",
                "/api/feed/posts",
                {"json": {"body": "Hi", "content_type": "note"}, "headers": headers},
            ),
            (
                "POST",
                "/api/feed/posts/pi-hannah-10k/comments",
                {"json": {"body": "Congrats!"}, "headers": headers},
            ),
            (
                "POST",
                "/api/feed/posts/pi-hannah-10k/reactions",
                {"json": {"reaction_type": "celebrate"}, "headers": headers},
            ),
            (
                "DELETE",
                "/api/feed/posts/pi-hannah-10k/reactions/celebrate",
                {"headers": headers},
            ),
            ("POST", "/api/feed/posts/pi-hannah-10k/save", {"headers": headers}),
        )
        for flag in (True, False):
            app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = flag
            for method, path, kwargs in requests:
                with self.subTest(flag=flag, method=method, path=path):
                    response = self.client.open(path, method=method, **kwargs)
                    self.assertEqual(response.status_code, 404)
        get_page.assert_not_called()
        get_post_detail.assert_not_called()


class PeopleInterestsServiceContractTests(unittest.TestCase):
    """Direct unit coverage of the untouched in-process service.

    The behaviors the retired routes used to exercise still hold at the
    service seam (services/people_interests_feed.py is unchanged by
    PS-COMMUNITY-AUTH-WALL-001).
    """

    def setUp(self):
        # A fresh feed per test so in-process writes never leak between tests.
        self.feed = PeopleInterestsFeed()

    def test_page_returns_items_and_cursor(self):
        page = self.feed.get_page(limit=16)
        self.assertEqual(len(page["items"]), 16)
        self.assertIsNotNone(page["next_cursor"])

    def test_cursor_pagination_is_stable_and_unduplicated(self):
        first = self.feed.get_page(limit=16)
        second = self.feed.get_page(limit=16, cursor=first["next_cursor"])
        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        self.assertFalse(first_ids & second_ids)
        # Repeating the same cursor returns the same page.
        repeat = self.feed.get_page(limit=16, cursor=first["next_cursor"])
        self.assertEqual(
            [item["id"] for item in second["items"]],
            [item["id"] for item in repeat["items"]],
        )

    def test_invalid_cursor_rejected(self):
        with self.assertRaises(FeedValidationError):
            self.feed.get_page(cursor="<script>alert(1)</script>")

    def test_detail_returns_full_text_and_comments(self):
        post = self.feed.get_post_detail("pi-maya-half")
        self.assertIn("half marathon", post["body"])
        self.assertEqual(len(post["comments"]), 5)
        self.assertEqual(post["comment_count"], 5)

    def test_unknown_post_raises_not_found(self):
        with self.assertRaises(FeedNotFoundError):
            self.feed.get_post_detail("pi-does-not-exist")

    def test_post_over_limit_rejected(self):
        with self.assertRaises(FeedValidationError):
            self.feed.create_post(
                "test-user-1", {}, "x" * (POST_BODY_MAX + 1), "note"
            )

    def test_unsupported_content_type_rejected(self):
        with self.assertRaises(FeedValidationError):
            self.feed.create_post("test-user-1", {}, "Hi", "advertisement")

    def test_new_posts_have_deterministic_layout(self):
        post = self.feed.create_post("test-user-1", {}, "Tiny note", "note")
        self.assertIn(
            post["layout"],
            {"small", "standard", "tall", "photo", "featured", "wide"},
        )
        again = self.feed.get_post_detail(post["id"])
        self.assertEqual(post["rotation"], again["rotation"])
        self.assertEqual(post["paper_color"], again["paper_color"])

    def test_created_post_never_echoes_a_foreign_user_key(self):
        post = self.feed.create_post(
            "test-user-1", {"display_name": "You"}, "Hello board", "note"
        )
        self.assertNotIn("someone-else", json.dumps(post))

    def test_reaction_add_and_remove_are_idempotent(self):
        base = self.feed.get_post_detail("pi-hannah-10k")["reactions"].get(
            "celebrate", 0
        )
        for _ in range(3):
            result = self.feed.add_reaction(
                "test-user-1", "pi-hannah-10k", "celebrate"
            )
        self.assertEqual(result["reactions"]["celebrate"], base + 1)
        for _ in range(2):
            result = self.feed.remove_reaction(
                "test-user-1", "pi-hannah-10k", "celebrate"
            )
        self.assertEqual(result["reactions"].get("celebrate", 0), base)

    def test_unsupported_reaction_rejected(self):
        with self.assertRaises(FeedValidationError):
            self.feed.add_reaction("test-user-1", "pi-hannah-10k", "dislike")

    def test_save_toggles(self):
        first = self.feed.toggle_save("test-user-1", "pi-hannah-10k")
        second = self.feed.toggle_save("test-user-1", "pi-hannah-10k")
        self.assertTrue(first["saved"])
        self.assertFalse(second["saved"])

    def test_comment_can_be_submitted_and_over_limit_rejected(self):
        comment = self.feed.add_comment(
            "test-user-1", {}, "pi-hannah-10k", "Congrats on the PR!"
        )
        detail = self.feed.get_post_detail("pi-hannah-10k")
        self.assertEqual(detail["comments"][-1]["body"], "Congrats on the PR!")
        self.assertEqual(comment["comment_count"], detail["comment_count"])
        with self.assertRaises(FeedValidationError):
            self.feed.add_comment("test-user-1", {}, "pi-hannah-10k", "x" * 301)


class PeopleInterestsFixtureTests(unittest.TestCase):
    """Guard the fixture contract the renderer and CSS rely on."""

    @classmethod
    def setUpClass(cls):
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "data", "people_interests_feed.json",
        )
        with open(fixture_path, "r", encoding="utf-8") as fixture_file:
            cls.fixture = json.load(fixture_file)

    def test_posts_respect_vocabularies_and_limits(self):
        layouts = {"small", "standard", "tall", "wide", "photo", "featured"}
        papers = {"sticky", "torn", "lined", "polaroid", "kraft", "quote"}
        for post in self.fixture["posts"]:
            self.assertIn(post["content_type"], CONTENT_TYPES, post["id"])
            self.assertIn(post["layout"], layouts, post["id"])
            self.assertIn(post["paper"], papers, post["id"])
            self.assertLessEqual(len(post.get("body", "")), POST_BODY_MAX, post["id"])
            self.assertLessEqual(abs(post["rotation"]), 6, post["id"])
            self.assertIn(post["author"], self.fixture["authors"], post["id"])
            for key in post.get("reactions", {}):
                self.assertIn(key, REACTION_KEYS, post["id"])

    def test_rotations_are_varied_not_uniform(self):
        rotations = [post["rotation"] for post in self.fixture["posts"]]
        straight = [r for r in rotations if r == 0]
        self.assertLessEqual(len(straight), 2)
        self.assertTrue(any(r < 0 for r in rotations))
        self.assertTrue(any(r > 0 for r in rotations))

    def test_photo_files_exist_and_pete_photos_stay_petes(self):
        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"
        )
        for post in self.fixture["posts"]:
            photo = post.get("photo")
            if not photo:
                continue
            for key in ("src", "full"):
                self.assertTrue(
                    os.path.exists(os.path.join(static_dir, photo[key])),
                    f"{post['id']}: missing {photo[key]}",
                )
            if "/pete" in photo["src"]:
                self.assertEqual(post["author"], "petec", post["id"])


class FeedV12RuleTests(unittest.TestCase):
    """PS-FEED-002: rail cleanup, Respond vocabulary, no Ask AI in Community.

    PS-COMMUNITY-AUTH-WALL-001: the page under guard is now the signed-in
    member Community — the only Community render. The Break panel left the
    response entirely, so the filler-module ban is page-wide again.
    """

    @classmethod
    def setUpClass(cls):
        cls.previous_config = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY="feed-rules-member",
            PEERSLATE_OWNER_USER_KEYS="someone-else-entirely",
            PEERSLATE_OWNER_EMAILS="",
        )
        cls.html = app.test_client().get("/the-slate").get_data(as_text=True)

    @classmethod
    def tearDownClass(cls):
        app.config.clear()
        app.config.update(cls.previous_config)

    def test_banned_rail_modules_removed_page_wide(self):
        # The retired People & Interests board's own filler-rail CSS hooks
        # never return anywhere on the page.
        for banned in ("pi-pickme", "pi-challenge", "pi-poll", "pi-sharegood"):
            self.assertNotIn(banned, self.html)

    def test_no_filler_modules_beside_the_feed_itself(self):
        # Page-wide now: the embedded Break panel (which legitimately kept
        # these cards) is retired along with the public shell.
        for banned in ("Community poll", "Weekend Challenge"):
            self.assertNotIn(banned, self.html)

    def test_respond_vocabulary(self):
        # The member Community is entirely client-rendered by community-v1.js
        # — the approved Respond vocabulary lives there, and the retired
        # feed-living-stream.js never loads on this page.
        self.assertIn('src="/static/js/community-v1.js', self.html)
        self.assertNotIn("feed-living-stream.js", self.html)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        js_path = os.path.join(root, "static", "js", "community-v1.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        for intent in ("celebrate", "support", "i_relate", "ask", "offer_help"):
            self.assertIn(intent, js)
        self.assertNotIn('"applaud"', js)
        self.assertNotIn("Rooting for you", js)

    def test_no_ask_ai_inside_community(self):
        self.assertNotIn("data-open-chat", self.html)
        self.assertNotIn('id="chat-toggle"', self.html)
        self.assertNotIn("Ask Pete AI", self.html)


if __name__ == "__main__":
    unittest.main()
