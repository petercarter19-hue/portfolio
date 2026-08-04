"""Removal revokes public access immediately, before any delayed purge.

Required evidence item 4 of the approved retention decision:
"Verify that removal immediately denies public detail, Feed, search, and
attachment routes before any delayed purge runs."

This is the boundary that makes the 30-day purge window safe. The purge is a
housekeeping delay, not the thing that protects a member: the instant an
author removes a post, every public route must stop serving it, with its text
still sitting in the database for the whole recovery window.

These tests assert the contract in the SQL that all public reads go through,
plus the API behaviour when a removed record yields nothing.
"""

import re
import unittest
from pathlib import Path
from unittest import mock

from app import app


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
)

# Every procedure a public visitor can reach.
PUBLIC_READ_PROCEDURES = (
    "usp_ListPublicCommunityFeed",
    "usp_GetPublicCommunityPost",
    "usp_ListPublicCommunityShelf",
    "usp_GetPublicCommunityContribution",
    "usp_SearchPublicCommunity",
    "usp_GetPublicCommunityMedia",
)


def procedure_body(name):
    """The exact body of one procedure.

    The trailing word boundary matters: without it
    usp_GetPublicCommunityMedia also matches
    usp_GetPublicCommunityMediaForOwner, which is an owner-only route with a
    deliberately different contract.
    """
    source = MIGRATION.read_text(encoding="utf-8")
    match = re.search(
        r"CREATE OR ALTER PROCEDURE dbo\." + name + r"\b.*?END'\);",
        source,
        re.S,
    )
    assert match, f"{name} not found in the migration"
    return match.group(0)


class RemovalDeniesPublicReadsTests(unittest.TestCase):
    def test_every_public_read_requires_a_live_publication_state(self):
        for name in PUBLIC_READ_PROCEDURES:
            with self.subTest(procedure=name):
                body = procedure_body(name)
                self.assertTrue(
                    "publication_state=N''published''" in body
                    or "lifecycle_state=N''active''" in body,
                    f"{name} can serve a removed record",
                )

    def test_every_public_read_excludes_held_and_removed_moderation(self):
        for name in PUBLIC_READ_PROCEDURES:
            with self.subTest(procedure=name):
                self.assertIn(
                    "moderation_state=N''clear''",
                    procedure_body(name),
                    f"{name} can serve held or removed material",
                )

    def test_attachments_require_their_parent_to_be_live(self):
        # An attachment outliving its post is the worst version of this bug:
        # the post disappears while its file stays fetchable by direct link.
        body = procedure_body("usp_GetPublicCommunityMedia")
        self.assertIn("media.removed_at_utc IS NULL", body)
        self.assertIn("direct_post.publication_state=N''published''", body)
        self.assertIn("contribution.lifecycle_state=N''active''", body)
        self.assertIn("contribution_post.publication_state=N''published''", body)
        self.assertIn("media.media_state=N''ready''", body)

    def test_public_reads_require_a_public_audience_not_merely_published(self):
        for name in ("usp_GetPublicCommunityPost", "usp_GetPublicCommunityMedia"):
            with self.subTest(procedure=name):
                self.assertIn("audience=N''public''", procedure_body(name))

    def test_removal_sets_the_state_the_reads_filter_on(self):
        # The delete path and the read path must agree, or one of them is
        # decorative. Delete flips publication_state to 'deleted'; the reads
        # above require 'published'.
        body = procedure_body("usp_DeletePublicCommunityPost")
        self.assertIn("publication_state=N''deleted''", body)
        self.assertIn("deleted_at_utc=SYSUTCDATETIME()", body)

    def test_removal_deletes_responses_and_saves_outright(self):
        # These are not purged later; they go immediately, because they point
        # at content that is no longer reachable.
        body = procedure_body("usp_DeletePublicCommunityPost")
        self.assertIn("DELETE dbo.community_responses", body)
        self.assertIn("DELETE dbo.community_saves", body)

    def test_purge_is_a_later_housekeeping_step_not_the_protection(self):
        # The purge runs 30 days after removal. If public denial depended on
        # it, content would stay readable for a month after deletion.
        retention = (
            ROOT
            / "SQL FIles"
            / "Migrations"
            / "proposed"
            / "PS-COMMUNITY-RETENTION-001_retention.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("deleted_at_utc <= @Cutoff", retention)
        # The purge only ever touches already-removed rows.
        self.assertIn("deleted_at_utc IS NOT NULL", retention)


class RemovedContentReturnsNotFoundTests(unittest.TestCase):
    """When the filtered read yields nothing, the route must 404, not 500."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = True
        self.client = app.test_client()

    def tearDown(self):
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False

    def test_a_removed_post_detail_reads_as_missing(self):
        key = "11111111-1111-1111-1111-111111111111"
        with mock.patch(
            "services.community_feed_service.community_feed_service.post_detail",
            side_effect=__import__(
                "services.community_contracts", fromlist=["x"]
            ).CommunityNotFoundError("gone"),
        ):
            response = self.client.get(f"/api/community/posts/{key}")
        self.assertEqual(response.status_code, 404)
        body = response.get_data(as_text=True).lower()
        # A neutral answer: never reveal that it existed and was removed.
        for leak in ("deleted", "removed", "purged", "retention"):
            with self.subTest(term=leak):
                self.assertNotIn(leak, body)


if __name__ == "__main__":
    unittest.main()
