"""People & Interests living board (PS-FEAT-002) — route, API, and fixture tests."""

import json
import os
import unittest
from unittest.mock import patch

from app import app
from services.people_interests_feed import (
    CONTENT_TYPES,
    POST_BODY_MAX,
    REACTION_KEYS,
    PeopleInterestsFeed,
)


SAME_ORIGIN = {"X-PeerSlate-Request": "same-origin"}


class PeopleInterestsPageTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_the_slate_landing_is_the_board(self):
        # The board took over /the-slate (Pete, 2026-07-14).
        response = self.client.get("/the-slate")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("People &amp; Interests", html)
        self.assertIn("pi-board", html)
        self.assertIn("pi-initial-feed", html)

    def test_old_board_address_forwards_to_the_slate(self):
        response = self.client.get("/the-slate/people-interests")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/the-slate"))

    def test_board_keeps_the_hub_links(self):
        html = self.client.get("/the-slate").get_data(as_text=True)
        self.assertIn("Slate Board", html)
        self.assertIn("My Slate", html)
        self.assertIn("Daily Slate", html)
        self.assertIn("/the-slate/my-slate", html)
        self.assertIn("/the-slate/daily", html)

    def test_page_keeps_existing_headers_and_feed_strip(self):
        html = self.client.get("/the-slate").get_data(as_text=True)
        # The untouched global header and profile sub-header render as-is.
        self.assertIn("platform-nav", html)
        self.assertIn("profile-tabs", html)
        # The current landing feed and honest News preview live in the
        # contextual strip; Break remains a valid route outside this bar.
        self.assertIn("People &amp; Interests", html)
        self.assertIn("News Feed", html)

    def test_existing_routes_unaffected(self):
        for path in ("/the-slate/break", "/the-slate/daily", "/the-slate/my-slate", "/the-slate/pulse"):
            response = self.client.get(path, base_url="http://localhost")
            self.assertEqual(response.status_code, 200, path)

    def test_no_category_filter_row_above_the_board(self):
        # The mockup's All/People/Goals/... filter buttons were intentionally
        # removed to give the board more space.
        html = self.client.get("/the-slate").get_data(as_text=True)
        self.assertNotIn("pi-filters", html)


class PeopleInterestsApiTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY"),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="test-user-1",
        )
        self.client = app.test_client()
        # A fresh feed per test so in-process writes never leak between tests.
        self.feed = PeopleInterestsFeed()
        self.feed_patch = patch(
            "people_interests_api.people_interests_feed", self.feed
        )
        self.feed_patch.start()

    def tearDown(self):
        self.feed_patch.stop()
        app.config.update(self.original_config)

    # ---- reads ----

    def test_feed_returns_items_and_cursor(self):
        response = self.client.get("/api/feed/people-interests?limit=16")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["items"]), 16)
        self.assertIsNotNone(payload["next_cursor"])

    def test_cursor_pagination_is_stable_and_unduplicated(self):
        first = self.client.get("/api/feed/people-interests?limit=16").get_json()
        second = self.client.get(
            "/api/feed/people-interests?limit=16&cursor=" + first["next_cursor"]
        ).get_json()
        first_ids = {item["id"] for item in first["items"]}
        second_ids = {item["id"] for item in second["items"]}
        self.assertFalse(first_ids & second_ids)
        # Repeating the same cursor returns the same page.
        repeat = self.client.get(
            "/api/feed/people-interests?limit=16&cursor=" + first["next_cursor"]
        ).get_json()
        self.assertEqual(
            [item["id"] for item in second["items"]],
            [item["id"] for item in repeat["items"]],
        )

    def test_invalid_cursor_rejected(self):
        response = self.client.get(
            "/api/feed/people-interests?cursor=<script>alert(1)</script>"
        )
        self.assertEqual(response.status_code, 400)

    def test_detail_returns_full_text_and_comments(self):
        response = self.client.get("/api/feed/posts/pi-maya-half")
        self.assertEqual(response.status_code, 200)
        post = response.get_json()["post"]
        self.assertIn("half marathon", post["body"])
        self.assertEqual(len(post["comments"]), 5)
        self.assertEqual(post["comment_count"], 5)

    def test_unknown_post_is_404(self):
        response = self.client.get("/api/feed/posts/pi-does-not-exist")
        self.assertEqual(response.status_code, 404)

    # ---- writes: protections ----

    def test_writes_require_same_origin_header(self):
        response = self.client.post(
            "/api/feed/posts", json={"body": "Hi", "content_type": "note"}
        )
        self.assertEqual(response.status_code, 403)

    def test_writes_require_identity(self):
        app.config.update(
            TESTING=False,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
        )
        response = self.client.post(
            "/api/feed/posts",
            headers=SAME_ORIGIN,
            json={"body": "Hi", "content_type": "note"},
        )
        self.assertEqual(response.status_code, 401)

    def test_browser_supplied_user_key_is_ignored(self):
        response = self.client.post(
            "/api/feed/posts",
            headers=SAME_ORIGIN,
            json={"body": "Hello board", "content_type": "note", "user_key": "someone-else"},
        )
        self.assertEqual(response.status_code, 201)
        post = response.get_json()["post"]
        self.assertNotIn("someone-else", json.dumps(post))

    # ---- writes: posts ----

    def test_valid_post_appears_in_feed(self):
        response = self.client.post(
            "/api/feed/posts",
            headers=SAME_ORIGIN,
            json={"body": "Shipped my study plan today.", "content_type": "win"},
        )
        self.assertEqual(response.status_code, 201)
        post = response.get_json()["post"]
        feed = self.client.get("/api/feed/people-interests?limit=5").get_json()
        self.assertEqual(feed["items"][0]["id"], post["id"])
        self.assertEqual(feed["items"][0]["body"], "Shipped my study plan today.")

    def test_post_over_limit_rejected(self):
        response = self.client.post(
            "/api/feed/posts",
            headers=SAME_ORIGIN,
            json={"body": "x" * (POST_BODY_MAX + 1), "content_type": "note"},
        )
        self.assertEqual(response.status_code, 400)

    def test_unsupported_content_type_rejected(self):
        response = self.client.post(
            "/api/feed/posts",
            headers=SAME_ORIGIN,
            json={"body": "Hi", "content_type": "advertisement"},
        )
        self.assertEqual(response.status_code, 400)

    def test_new_posts_have_deterministic_layout(self):
        response = self.client.post(
            "/api/feed/posts",
            headers=SAME_ORIGIN,
            json={"body": "Tiny note", "content_type": "note"},
        )
        post = response.get_json()["post"]
        self.assertIn(post["layout"], {"small", "standard", "tall", "photo", "featured", "wide"})
        again = self.client.get("/api/feed/posts/" + post["id"]).get_json()["post"]
        self.assertEqual(post["rotation"], again["rotation"])
        self.assertEqual(post["paper_color"], again["paper_color"])

    # ---- writes: comments ----

    def test_comment_can_be_submitted(self):
        response = self.client.post(
            "/api/feed/posts/pi-hannah-10k/comments",
            headers=SAME_ORIGIN,
            json={"body": "Congrats on the PR!"},
        )
        self.assertEqual(response.status_code, 201)
        detail = self.client.get("/api/feed/posts/pi-hannah-10k").get_json()["post"]
        self.assertEqual(detail["comments"][-1]["body"], "Congrats on the PR!")

    def test_comment_over_limit_rejected(self):
        response = self.client.post(
            "/api/feed/posts/pi-hannah-10k/comments",
            headers=SAME_ORIGIN,
            json={"body": "x" * 301},
        )
        self.assertEqual(response.status_code, 400)

    # ---- writes: reactions ----

    def test_reaction_add_and_remove_are_idempotent(self):
        base = self.feed.get_post_detail("pi-hannah-10k")["reactions"].get("applaud", 0)
        for _ in range(3):
            response = self.client.post(
                "/api/feed/posts/pi-hannah-10k/reactions",
                headers=SAME_ORIGIN,
                json={"reaction_type": "applaud"},
            )
            self.assertEqual(response.status_code, 200)
        after_adds = response.get_json()["reactions"]["applaud"]
        self.assertEqual(after_adds, base + 1)

        for _ in range(2):
            response = self.client.delete(
                "/api/feed/posts/pi-hannah-10k/reactions/applaud",
                headers=SAME_ORIGIN,
            )
            self.assertEqual(response.status_code, 200)
        after_removes = response.get_json()["reactions"].get("applaud", 0)
        self.assertEqual(after_removes, base)

    def test_unsupported_reaction_rejected(self):
        response = self.client.post(
            "/api/feed/posts/pi-hannah-10k/reactions",
            headers=SAME_ORIGIN,
            json={"reaction_type": "dislike"},
        )
        self.assertEqual(response.status_code, 400)

    def test_save_toggles(self):
        first = self.client.post(
            "/api/feed/posts/pi-hannah-10k/save", headers=SAME_ORIGIN
        ).get_json()
        second = self.client.post(
            "/api/feed/posts/pi-hannah-10k/save", headers=SAME_ORIGIN
        ).get_json()
        self.assertTrue(first["saved"])
        self.assertFalse(second["saved"])


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


if __name__ == "__main__":
    unittest.main()
