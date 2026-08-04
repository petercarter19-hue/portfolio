"""The Recently deleted recovery screen.

Guards the boundary that matters most: this page is the author's own recovery
window, and nobody else may reach it or act through it.
"""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from app import app
from services.community_contracts import (
    CommunityNotFoundError,
    CommunityUnavailableError,
)
from services.community_restore_service import CommunityRestoreService
from services.database_service import DatabaseServiceError


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "community_recently_deleted.html"
STYLES = ROOT / "static" / "css" / "community-v1.css"


def restorable_row(kind="post"):
    return {
        "record_key": "11111111-1111-1111-1111-111111111111",
        "record_kind": kind,
        "body": "A thing I wrote and then removed.",
        "deleted_at_utc": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "restorable_until_utc": datetime(2026, 8, 31, tzinfo=timezone.utc),
    }


class RestoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = mock.Mock()
        self.service = CommunityRestoreService(database=self.database)

    def test_listing_presents_only_bounded_fields(self):
        self.database.first_result.return_value = [restorable_row()]
        items = self.service.list_restorable("owner-key")
        self.assertEqual(len(items), 1)
        self.assertEqual(
            set(items[0]),
            {
                "record_key",
                "record_kind",
                "excerpt",
                "truncated",
                "deleted_on",
                "recoverable_until",
            },
        )

    def test_a_long_body_is_excerpted_rather_than_sent_whole(self):
        row = restorable_row()
        row["body"] = "x" * 400
        self.database.first_result.return_value = [row]
        item = self.service.list_restorable("owner-key")[0]
        self.assertEqual(len(item["excerpt"]), 280)
        self.assertTrue(item["truncated"])

    def test_someone_elses_record_is_indistinguishable_from_no_record(self):
        self.database.first_row.return_value = {"outcome": "not_found"}
        with self.assertRaises(CommunityNotFoundError):
            self.service.restore_post("owner-key", restorable_row()["record_key"])

    def test_every_sql_outcome_is_passed_through_verbatim(self):
        for outcome in ("restored", "existing", "purged", "held", "expired"):
            with self.subTest(outcome=outcome):
                self.database.first_row.return_value = {"outcome": outcome}
                self.assertEqual(
                    self.service.restore_post(
                        "owner-key", restorable_row()["record_key"]
                    ),
                    outcome,
                )

    def test_an_unrecognised_outcome_is_refused_rather_than_trusted(self):
        self.database.first_row.return_value = {"outcome": "something_new"}
        with self.assertRaises(CommunityUnavailableError):
            self.service.restore_post("owner-key", restorable_row()["record_key"])

    def test_a_database_failure_never_leaks_as_a_success(self):
        self.database.first_result.side_effect = DatabaseServiceError("down")
        with self.assertRaises(CommunityUnavailableError):
            self.service.list_restorable("owner-key")


class RecentlyDeletedIsReachableTests(unittest.TestCase):
    """The page shipped with no way to reach it.

    It is linked from the existing policy line on the feed rather than from a
    new navigation surface, and only for the owner: a public visitor must not
    learn that a recovery page exists, which is the same reasoning behind the
    route returning 404 rather than 403.
    """

    FEED = ROOT / "templates" / "community_feed.html"

    @classmethod
    def setUpClass(cls):
        cls.feed = cls.FEED.read_text(encoding="utf-8")

    def test_the_feed_links_to_the_page(self):
        self.assertIn(
            "url_for('community_routes.community_recently_deleted')", self.feed
        )

    def test_the_link_is_owner_only(self):
        start = self.feed.index('<p class="cv1-policy-line">')
        line = self.feed[start : self.feed.index("</p>", start)]
        self.assertIn("community_recently_deleted", line)
        self.assertIn("{% if community_owner %}", line)
        self.assertLess(
            line.index("{% if community_owner %}"),
            line.index("community_recently_deleted"),
            "the link must sit inside the owner-only branch",
        )

    def test_it_reuses_the_existing_policy_line_rather_than_new_navigation(self):
        # A new permanent navigation layer needs approved route authority.
        # This is the component that already carries Community's secondary
        # links, so no new surface is introduced.
        self.assertEqual(self.feed.count('<p class="cv1-policy-line">'), 1)
        self.assertIn("Policy, reporting, and takedown contact", self.feed)


class RecentlyDeletedRouteTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_the_page_is_absent_while_the_flag_is_off(self):
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False
        self.assertEqual(
            self.client.get("/the-slate/recently-deleted").status_code, 404
        )
        self.assertEqual(
            self.client.post("/the-slate/recently-deleted/restore").status_code, 404
        )

    def test_a_non_owner_gets_a_neutral_404_not_a_403(self):
        # A 403 would confirm the page exists and that someone has removed
        # content worth looking at. 404 reveals nothing.
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = True
        try:
            with mock.patch(
                "community_routes.viewer_context",
                return_value={
                    "community_owner": False,
                    "community_signed_in": True,
                    "community_display_name": None,
                    "community_draft_namespace": None,
                },
            ):
                self.assertEqual(
                    self.client.get("/the-slate/recently-deleted").status_code, 404
                )
                self.assertEqual(
                    self.client.post(
                        "/the-slate/recently-deleted/restore",
                        data={"record_kind": "post", "record_key": "x"},
                    ).status_code,
                    404,
                )
        finally:
            app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False


class RecentlyDeletedPresentationTests(unittest.TestCase):
    def test_the_page_states_the_window_and_what_is_not_restored(self):
        markup = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("retention_days", markup)
        # The honest limits must be on the page, not only in the docs.
        self.assertIn("permanently erased", markup)
        self.assertIn("not restored", markup)

    def test_restore_is_a_form_post_rather_than_a_link(self):
        # A GET link would let a prefetcher or crawler restore content.
        markup = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('method="post"', markup)
        self.assertNotIn("cv1-recover-action\" href", markup)

    def test_the_screen_follows_the_existing_page_shell(self):
        markup = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('{% extends "base.html" %}', markup)
        self.assertIn("cv1-policy", markup)
        self.assertIn("community-v1.css", markup)

    def test_no_dark_theme_rules_were_added_for_this_screen(self):
        # Pete, 2026-08-03: dark is not being carried forward for now.
        styles = STYLES.read_text(encoding="utf-8")
        for line in styles.splitlines():
            if "cv1-recover" in line:
                with self.subTest(line=line.strip()[:60]):
                    self.assertNotIn('data-theme="dark"', line)

    def test_every_action_meets_the_touch_target_minimum(self):
        styles = STYLES.read_text(encoding="utf-8")
        action = next(
            line for line in styles.splitlines()
            if line.startswith(".cv1-recover-action {")
        )
        self.assertIn("min-height: 44px", action)


if __name__ == "__main__":
    unittest.main()
